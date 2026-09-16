"""Plot recorded s-204 fields for expert review. No solver/API/grader mutation."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from scipy.spatial import cKDTree

from agentcfd_bench.foam.parsed import read
from agentcfd_bench.foam.science_metrics import field_values
from agentcfd_bench.journal import read_receipt
from agentcfd_bench.identity import fingerprint
from agentcfd_bench.task_package import PROJECT

SOURCES = [
    ('原数值策略 · 78,750 单元', 'audits/free-mesh-buoyant-shock-20260915-001/s-204/native/runs/r-000001'),
    ('最后的一阶迎风方案 · 40,320 单元', 'audits/free-mesh-buoyant-shock-20260915-004/s-204/native/runs/r-000010'),
]


def midplane_values(centres, values, query, z=0.):
    """One consistent plane: interpolate between the two bracketing z layers.

    Do not let nearest-neighbour ties select +/- z randomly at different pixels.
    In-plane sampling stays nearest-cell, without smoothing boundary layers.
    """
    zs = np.unique(np.round(centres[:, 2], 10))
    if z < zs.min() or z > zs.max():
        raise ValueError('Requested slice outside native cell-centre layers')
    below, above = zs[zs <= z][-1], zs[zs >= z][0]
    samples = []
    for plane in (below, above):
        subset = np.flatnonzero(np.isclose(centres[:, 2], plane, atol=1e-9, rtol=0))
        _, indices = cKDTree(centres[subset, :2]).query(query[:, :2])
        samples.append(values[subset[indices]])
    weight = 0. if below == above else (z-below)/(above-below)
    return samples[0]*(1-weight)+samples[1]*weight, [float(below), float(above)]


def difference(before, after):
    delta = after-before
    return np.linalg.norm(delta, axis=-1) if delta.ndim == 3 else delta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--all-fields', action='store_true', help='Also plot velocity, total and reduced pressure')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    font = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),
                         'font.size':11, 'axes.unicode_minus':False, 'pdf.fonttype':42})
    x = np.linspace(0, .076, 150)
    y = np.linspace(0, 2.18, 480)
    xx, yy = np.meshgrid(x, y)
    query = np.column_stack((xx.ravel(), yy.ravel(), np.zeros(xx.size)))
    rows = []
    provenance = []
    for title, source in SOURCES:
        root = PROJECT/source
        native = read_receipt(root/'result.json')
        if native['verdict'] != 'pass' or read_receipt(root/'released.json') != {'released':True}:
            raise ValueError('Only completed, released native results may be plotted')
        artifacts = native['artifacts']
        if fingerprint(artifacts) != native['artifact_hash']:
            raise ValueError('Native field evidence changed')
        count = int(read(artifacts['6000/C'])['internalField'][2])
        c = np.asarray(field_values(artifacts['6000/C'], 'C', count, '[0 1 0 0 0 0 0]', 6000))
        dimensions = {'T':'[0 0 0 1 0 0 0]'}
        if args.all_fields:
            dimensions.update(U='[0 1 -1 0 0 0 0]', p='[1 -1 -2 0 0 0 0]', p_rgh='[1 -1 -2 0 0 0 0]')
        fields, diagnostics = {}, {}
        for name, dimension in dimensions.items():
            actual = [np.asarray(field_values(artifacts[f'{t}/{name}'], name, count, dimension, t)) for t in (5950, 6000)]
            panels = []
            for values in actual:
                sampled, layers = midplane_values(c, values, query)
                panels.append(sampled.reshape((*xx.shape, 3) if name == 'U' else xx.shape))
            delta = difference(*panels)
            full_delta = actual[1]-actual[0]
            if name == 'U':
                full_delta = np.linalg.norm(full_delta, axis=1)
            fields[name] = panels
            diagnostics[name] = {'slice_change_min':float(delta.min()), 'slice_change_max':float(delta.max()),
                                 'full_field_change_min':float(full_delta.min()), 'full_field_change_max':float(full_delta.max())}
        rows.append((title, fields))
        record = {'title':title, 'source':source, 'native_result_hash':fingerprint(native),
                  'iterations':[5950,6000], 'sample_plane_z_m':0,
                  'bracketing_cell_z_m':layers, 'slice_method':'linear in z, nearest native cell in x/y',
                  'field_changes':diagnostics}
        provenance.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    names = {'T':('温度 T', 'K', 'temperature'), 'U':('速度 |U|', 'm/s', 'velocity'),
             'p':('总压力 p − 100000 Pa', 'Pa', 'pressure'), 'p_rgh':('去静水项压力 p_rgh', 'Pa', 'reduced_pressure')}
    for name in rows[0][1]:
        label, unit, filename = names[name]
        raw = [panels[name] for _, panels in rows]
        shown = [[np.linalg.norm(v, axis=-1) if name=='U' else v-(100000 if name=='p' else 0) for v in pair] for pair in raw]
        low, high = (288.15,307.75) if name=='T' else (min(float(a.min()) for pair in shown for a in pair), max(float(a.max()) for pair in shown for a in pair))
        limit = max(float(abs(difference(*pair)).max()) for pair in raw)
        fig, axes = plt.subplots(2,3, figsize=(12,10.5), layout='constrained')
        fig.suptitle('s-204 '+label+'：5950 次、6000 次及变化', fontsize=17)
        for i, (title, _) in enumerate(rows):
            for j, values in enumerate([*shown[i], difference(*raw[i])]):
                ax = axes[i,j]
                cmap, vmin, vmax = ('inferno' if name=='T' else 'viridis',low,high) if j<2 else ('magma' if name=='U' else 'RdBu_r',0 if name=='U' else -limit,limit)
                im = ax.imshow(values, origin='lower', extent=[0,76,0,2180], aspect='auto',
                               interpolation='nearest', cmap=cmap, vmin=vmin, vmax=vmax)
                text = ['5950 次', '6000 次', '|U(6000) − U(5950)|' if name=='U' else '6000 次 − 5950 次'][j]
                ax.set(title=title+'\n'+text+' / '+unit, xlabel='x / mm（左冷壁，右热壁）', ylabel='y / mm')
                ax.set_xticks([0,38,76])
                if name=='U' and j<2:
                    iy = np.arange(16,480,25); ix=np.arange(6,150,13)
                    uv=raw[i][j][np.ix_(iy,ix)]
                    vx,vy=uv[:,:,0]/.076, uv[:,:,1]/2.18
                    norm=np.maximum(np.hypot(vx,vy),1e-14)
                    ax.quiver(xx[np.ix_(iy,ix)]*1000, yy[np.ix_(iy,ix)]*1000, vx/norm*2.5, vy/norm*65,
                              angles='xy',scale_units='xy',scale=1,color='white',width=.003,alpha=.8)
                if j==1:
                    fig.colorbar(im, ax=axes[i,:2], label=label+' / '+unit, fraction=.04, pad=.02)
                elif j==2:
                    fig.colorbar(im, ax=ax, label='变化 / '+unit, fraction=.06, pad=.02)
        note='速度图白箭头仅示面内方向；变化图是向量差的模。' if name=='U' else '两方案使用统一色标；右列变化图另用统一色标。'
        fig.supxlabel('真实 OpenFOAM 场；z = 0 中面（厚度方向线性插值，面内最近单元，无平滑）。\n高 2180 mm、宽 76 mm，横向放大显示；'+note+'迭代次数不是物理时间。', fontsize=9)
        fig.savefig(args.output/('s204_'+filename+'.png'), dpi=165, facecolor='white')
        fig.savefig(args.output/('s204_'+filename+'.pdf'), facecolor='white')
        plt.close(fig)
    (args.output/'sources.json').write_text(json.dumps({'native_runs_started':0,'sources':provenance}, ensure_ascii=False, indent=2)+'\n')
    print('Saved '+str(args.output), flush=True)


if __name__ == '__main__':
    main()
