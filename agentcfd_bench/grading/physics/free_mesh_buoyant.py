"""Pure numeric extraction/comparison migrated from free_mesh_buoyant; no runtime policy."""
import math
import re
from .evaluation import native_output_reader
from .foam.parsed import read
from .foam.science_metrics import field_values, number
from .free_mesh_shock import GAS_R, field_at, native_fields

VERSION='free-mesh-buoyant-steady-v1'

BOUNDS=((0.,.076),(0.,2.18),(-.26,.26))

VOLUME = .076 * 2.18 * .52

PATCHES={'hot','cold','frontAndBack','topAndBottom'}

DT=307.75-288.15

BINS=20

DIMENSIONS={'C':'[0 1 0 0 0 0 0]','V':'[0 3 0 0 0 0 0]',
    'U':'[0 1 -1 0 0 0 0]','T':'[0 0 0 1 0 0 0]',
    'p':'[1 -1 -2 0 0 0 0]','p_rgh':'[1 -1 -2 0 0 0 0]',
    'k':'[0 2 -2 0 0 0 0]','omega':'[0 0 -1 0 0 0 0]',
    'nut':'[0 2 -1 0 0 0 0]','alphat':'[1 -1 -1 0 0 0 0]'}

SCHEMA={'final_iteration':('1',1),'cell_count':('1',1),'volume':('m3',1),
    'mass':('kg',1),'T_volume_mean':('K',1),'p_volume_mean':('Pa',1),
    'speed_volume_rms':('m/s',1),'U_volume_mean':('m/s',3),
    'last_initial_residual':('1',1),'last_final_residual':('1',1),
    'p_rgh_final_initial_residual':('1',1),'h_final_initial_residual':('1',1),
    'T_last_write_relative_change':('1',1),'U_last_write_relative_change':('1',1),
    **{n+'_wall_heat_rate':('W',1) for n in sorted(PATCHES)},
    **{n+'_volume_mean':(u,1) for n,u in [('k','m2/s2'),('omega','1/s'),('nut','m2/s'),('alphat','kg/(m s)')]},
    'T_x_bin_mean':('K',BINS),'Uy_x_bin_mean':('m/s',BINS),
    'T_y_bin_mean':('K',BINS),'Uy_y_bin_mean':('m/s',BINS)}

POLICY={'version':VERSION,'residuals':{'p_rgh':1e-4,'h':1e-4,'k':1e-3,'omega':1e-3},'mass_relative':1e-4,
    'optional_velocity_residual':1e-4,
    'wall_balance_relative':.01,'adiabatic_relative':1e-5,
    'stationarity_T_relative':.001,'stationarity_U_relative':.01,
    'T_profile_scaled_l1':.05,'U_profile_relative_l1':.10,'heat_transfer_relative':.05}

def last_iteration(log):
    matches=list(re.finditer(r'^Time = ([^\s]+)\s*$',log,re.M))
    if (not matches or not re.search(r'^End\s*$',log,re.M)
            or any(number(a[1])>=number(b[1]) for a,b in zip(matches,matches[1:]))):
        raise ValueError('Monotone completed native iteration log required')
    return number(matches[-1][1]),log[matches[-1].end():]

def wall_heat_rates(artifacts,end):
    # This v2306 log line reports gSum(mesh.magSf()*wallHeatFlux), in W.
    log=artifacts.get('wall_heat_flux.log','')
    times=[number(v) for v in re.findall(r'^Time = ([^\s]+)\s*$',log,re.M)]
    if len(times)!=1 or abs(times[0]-end)>1e-7 or not re.search(r'^End\s*$',log,re.M):
        raise ValueError('Wall heat flux must belong to the actual final native iteration')
    rows=re.findall(r'^\s*min/max/integ\(([A-Za-z0-9_]+)\) = ([^,\s]+), ([^,\s]+), ([^,\s]+)\s*$',log,re.M)
    if len(rows)!=4 or {r[0] for r in rows}!=PATCHES:
        raise ValueError('Exactly four native area-integrated wall heat rates required')
    values={name:number(integral) for name,_,_,integral in rows}
    for _,lo,hi,_ in rows:
        if number(lo)>number(hi): raise ValueError('Invalid native wall heat extrema')
    # Require the independently generated field too, with correct units/location.
    tree=read(field_at(artifacts,'wallHeatFlux',end)); header=tree.get('FoamFile',{})
    if (header.get('object')!=('wallHeatFlux',) or header.get('class')!=('volScalarField',)
            or header.get('format')!=('ascii',)
            or tuple(tree.get('dimensions',()))!=('[','1','0','-3','0','0','0','0',']')
            or abs(number(header.get('location',('nan',))[0].strip('"'))-end)>1e-7
            or set(tree.get('boundaryField',{}))!=PATCHES):
        raise ValueError('Native wallHeatFlux field identity/units/patches mismatch')
    return values

def cartesian_cells(centres,volumes):
    """Reconstruct tensor-product orthogonal cells without prescribing resolution.

    At this release non-Cartesian mesh representations remain explicit unsupported
    inputs; volume cannot be assigned to arbitrary bins by nearest cell centre.
    """
    axes=[]; coordinate_maps=[]
    for axis,(lo,hi) in enumerate(BOUNDS):
        # Geometrically aligned centres produced by native arithmetic are not
        # necessarily bit-identical. Cluster only within serialization roundoff,
        # then still prove complete unique cells and their actual native volumes.
        tolerance=max(1e-12,(hi-lo)*1e-8)
        groups=[]
        for value in sorted(set(row[axis] for row in centres)):
            if not groups or value-groups[-1][0]>tolerance: groups.append([value])
            else: groups[-1].append(value)
        mapping={v:math.fsum(group)/len(group) for group in groups for v in group}
        coords=sorted(set(mapping.values())); intervals={}; left=lo
        for c in coords:
            right=2*c-left
            if right<=left: raise ValueError('Native Cartesian cell ordering invalid')
            intervals[c]=(left,right); left=right
        if abs(left-hi)>1e-7: raise ValueError('Native cells do not cover supplied geometry')
        axes.append(intervals)
        coordinate_maps.append(mapping)
    mapped=[tuple(coordinate_maps[j][c[j]] for j in range(3)) for c in centres]
    if math.prod(len(a) for a in axes)!=len(centres) or len(set(mapped))!=len(centres):
        raise ValueError('Complete unique Cartesian tensor grid required')
    boxes=[]
    for centre,volume in zip(mapped,volumes):
        box=tuple(axes[j][centre[j]] for j in range(3))
        wanted=math.prod(hi-lo for lo,hi in box)
        if abs(volume-wanted)>1e-7*volume+1e-12: raise ValueError('Native C/V inconsistent with Cartesian mesh')
        boxes.append(box)
    return boxes

def bin_mean(boxes,volumes,values,axis):
    low,high=BOUNDS[axis]; width=(high-low)/BINS; result=[]
    for j in range(BINS):
        a,b=low+j*width,low+(j+1)*width
        weights=[max(0.,min(b,box[axis][1])-max(a,box[axis][0]))/
                 (box[axis][1]-box[axis][0])*v for box,v in zip(boxes,volumes)]
        total=math.fsum(weights)
        if total<=0: raise ValueError('Empty public observation bin')
        result.append(math.fsum(w*v for w,v in zip(weights,values))/total)
    return result

@native_output_reader
def snapshot(artifacts):
    log=artifacts.get('solver.log',''); end,last=last_iteration(log)
    data=native_fields(artifacts,end,DIMENSIONS)
    if any(v<=0 for v in data['T']):
        raise ValueError('Nonpositive absolute temperature is not physically realizable')
    boxes=cartesian_cells(data['C'],data['V'])
    volume=math.fsum(data['V'])
    def mean(values): return math.fsum(v*w for v,w in zip(values,data['V']))/volume
    residuals={}; outer_residuals={}
    for name in POLICY['residuals']:
        rows=re.findall(r'Solving for '+name+r', Initial residual = ([^,\s]+), Final residual = ([^,\s]+)',last)
        if not rows: raise ValueError('Final native residual missing: '+name)
        residuals[name]=[number(v) for v in rows[-1]]
        outer_residuals[name]=max(number(row[0]) for row in rows)
        if min(residuals[name])<0: raise ValueError('Negative native residual')
    optional_velocity_residuals={}
    for name in ('Ux','Uy','Uz'):
        rows=re.findall(r'Solving for '+name+r', Initial residual = ([^,\s]+), Final residual = ([^,\s]+)',last)
        if rows:
            vals=[number(row[0]) for row in rows]
            if min(vals)<0: raise ValueError('Negative native velocity residual')
            optional_velocity_residuals[name]=max(vals)
    previous=sorted(set(number(p.split('/')[0]) for p in artifacts
        if re.fullmatch(r'[0-9.eE+\-]+/U',p) and 0<number(p.split('/')[0])<end))
    if not previous: raise ValueError('Steady field stability needs a preceding native field write')
    prior=previous[-1]
    before={n:field_values(field_at(artifacts,n,prior),n,len(data['C']),DIMENSIONS[n],prior) for n in ('T','U')}
    thermal_change=mean([abs(a-b) for a,b in zip(data['T'],before['T'])])/DT
    velocity_scale=math.sqrt(mean([sum(x*x for x in row) for row in data['U']]))
    velocity_change=math.sqrt(mean([sum((a-b)**2 for a,b in zip(x,y))
        for x,y in zip(data['U'],before['U'])]))/max(velocity_scale,1e-12)
    heat=wall_heat_rates(artifacts,end)
    values={'final_iteration':end,'cell_count':len(data['C']),'volume':volume,
        'mass':mean([p/(GAS_R*T) for p,T in zip(data['p'],data['T'])])*volume,
        'T_volume_mean':mean(data['T']),'p_volume_mean':mean(data['p']),
        'speed_volume_rms':velocity_scale,
        'U_volume_mean':[mean([u[j] for u in data['U']]) for j in range(3)],
        'last_initial_residual':residuals['p_rgh'][0],'last_final_residual':residuals['p_rgh'][1],
        'p_rgh_final_initial_residual':residuals['p_rgh'][0],'h_final_initial_residual':residuals['h'][0],
        'T_last_write_relative_change':thermal_change,'U_last_write_relative_change':velocity_change,
        **{n+'_wall_heat_rate':v for n,v in heat.items()},
        **{n+'_volume_mean':mean(data[n]) for n in ('k','omega','nut','alphat')},
        **{n+'_'+label+'_bin_mean':bin_mean(boxes,data['V'],
            data['T'] if n=='T' else [u[1] for u in data['U']],axis)
            for n in ('T','Uy') for label,axis in [('x',0),('y',1)]}}
    return {'measurements':{k:{'unit':SCHEMA[k][0],'value':v} for k,v in values.items()},
        'data':data,'residuals':residuals,'outer_residuals':outer_residuals,
        'optional_velocity_residuals':optional_velocity_residuals,'previous_write':prior,
        'convergence_claim':bool(re.search(r'^SIMPLE solution converged in '+re.escape(str(int(end)))+
            r' iterations\s*$',log,re.M)),'heat':heat}
