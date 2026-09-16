"""Pure numeric extraction/comparison migrated from free_mesh_thermal; no runtime policy."""
import math
import re
from .evaluation import native_output_reader
from .completion import EDGE_REGIONS, Completion as ExecutionSpec
from .foam.parsed import canonical, read
from .foam.science_metrics import field_values, number
from .tutorial_tasks import list_values

VERSION = 'thermal-spatial-observations-v1'

DIMENSIONS = {'U':'[0 1 -1 0 0 0 0]', 'T':'[0 0 0 1 0 0 0]',
    'p':'[1 -1 -2 0 0 0 0]', 'p_rgh':'[1 -1 -2 0 0 0 0]',
    'C':'[0 1 0 0 0 0 0]', 'V':'[0 3 0 0 0 0 0]',
    'k':'[0 2 -2 0 0 0 0]', 'epsilon':'[0 2 -3 0 0 0 0]',
    'nut':'[0 2 -1 0 0 0 0]'}

REGIONS = {'s-202':EDGE_REGIONS, 's-203':('',)}

VOLUMES = {'bottomWater':0.0007786666666666667, 'topAir':0.00064,
           'heater':0.00004266666666666667, 'leftSolid':0.00006933333333333333,
           'rightSolid':0.00006933333333333333, '':0.000248}

def _check_task(task_id):
    if task_id not in REGIONS:
        raise ValueError('Unknown thermal task')

def _field_path(artifacts, field, end, region=''):
    suffix = (region+'/' if region else '')+field
    matches = [name for name in artifacts if re.fullmatch(r'[0-9.eE+\-]+/'+re.escape(suffix),name)
               and abs(number(name.split('/')[0])-end) <= 1e-7]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous final native field: '+suffix)
    return matches[0]

def _array(value, *, vector=False, count=None):
    if value[:1] == ('uniform',):
        item = [number(x) for x in list_values(value[1:])] if vector else number(value[1])
        if count is None:
            if not vector and item == 0:
                return []  # a uniform-zero face field has zero sum for any count
            raise ValueError('Native face count required for nonzero uniform field')
        return [item for _ in range(count)]
    kind = 'List<vector>' if vector else 'List<scalar>'
    if len(value)<5 or value[:2] != ('nonuniform',kind):
        raise ValueError('Expected explicit native face values')
    size = number(value[2])
    if not size.is_integer() or not 0 <= size <= 1000000:
        raise ValueError('Invalid face count')
    data = list_values(value[3:])
    if len(data) != size or (count is not None and count != size):
        raise ValueError('Native face list size mismatch')
    if vector:
        if any(not isinstance(v,list) or len(v)!=3 for v in data):
            raise ValueError('Native face vector shape')
        return [[number(x) for x in v] for v in data]
    if any(isinstance(v,list) for v in data):
        raise ValueError('Scalar face values required')
    return [number(v) for v in data]

def flux_observations(artifacts, task_id, end, region=''):
    """Use native face flux, never infer flow from unweighted boundary velocity."""
    phi = read(artifacts[_field_path(artifacts,'phi',end,region)])
    header = phi.get('FoamFile',{})
    if (header.get('class') != ('surfaceScalarField',) or header.get('object') != ('phi',)
            or header.get('format') != ('ascii',)):
        raise ValueError('Native phi header mismatch')
    expected_dims = '[1 0 -1 0 0 0 0]' if task_id == 's-202' else '[0 3 -1 0 0 0 0]'
    if canonical(phi['dimensions']) != canonical(read('x '+expected_dims+';')['x']):
        raise ValueError('Native mass/volume flux dimensions mismatch')
    location = header.get('location', ('',))[0].strip('"')
    if not region:
        if abs(number(location)-end)>1e-7:
            raise ValueError('Native phi location mismatch')
    else:
        parts=location.split('/')
        if len(parts)!=2 or parts[1]!=region or abs(number(parts[0])-end)>1e-7:
            raise ValueError('Native phi region/location mismatch')
    ctree = read(artifacts[_field_path(artifacts,'C',end,region)])
    ttree = read(artifacts[_field_path(artifacts,'T',end,region)])
    sums={}; enthalpy={}
    for name, boundary in phi.get('boundaryField',{}).items():
        cvalues = ctree.get('boundaryField',{}).get(name,{}).get('value',())
        count = len(_array(cvalues,vector=True)) if cvalues[:1] == ('nonuniform',) else None
        values = _array(boundary.get('value',()),count=count)
        sums[name] = math.fsum(values)
        if any(q != 0 for q in values):
            temperatures=_array(ttree['boundaryField'][name]['value'],count=len(values))
            rho = 1.2 if task_id=='s-203' else 1.0
            cp = 4181.0 if region=='bottomWater' else 1000.0
            enthalpy[name] = math.fsum(q*rho*cp*(t-300.0) for q,t in zip(values,temperatures))
        else:
            enthalpy[name] = 0.0
    openings = ('minX','maxX') if region else ('inlet','outlet1','outlet2')
    if not set(openings) <= sums.keys():
        raise ValueError('Native flow openings missing')
    denominator=math.fsum(abs(v) for v in sums.values())/2
    if denominator <= 0:
        raise ValueError('Expected nonzero throughflow')
    return {'unit':'kg/s' if region else 'm3/s', 'boundary_flux':sums,
            'relative_net_flux':abs(math.fsum(sums.values()))/denominator,
            'sensible_enthalpy_outflow_W':enthalpy,
            'note':'Air is compressible: net flux alone is NOT transient mass-balance error.'}

def region_at(point):
    """Confirmed material geometry in metres, independent of cell selection."""
    x,y,z=point
    if not (-.1 < x < .1 and -.04 < y < .04 and -.05 < z < .05):
        raise ValueError('Cell outside physical CHT geometry')
    if y > .008:
        return 'topAir'
    if abs(x) < .013333333333333333 and (y>0 or abs(z)<.01):
        return 'heater'
    if y>0:
        return 'leftSolid' if x<0 else 'rightSolid'
    return 'bottomWater'

def spatial_bin(task_id, region, point):
    """Fixed physical subvolumes; no mapping by reference cell number."""
    x,y,z=point
    if task_id=='s-203':
        if not 0<z<.02:
            raise ValueError('Cell outside T-junction thickness')
        if 0<x<.2 and -.01<y<.01:
            return 'inlet_'+str(min(4,int(x/.04)))
        if .2<x<.22 and -.21<y<.21:
            if y<-.01:
                return 'lower_'+str(min(4,int((y+.21)/.04)))
            if y>.01:
                return 'upper_'+str(min(4,int((y-.01)/.04)))
            return 'junction'
        raise ValueError('Cell outside T-junction geometry')
    if region_at(point)!=region:
        raise ValueError('Native cell assigned to wrong physical material')
    # Physical slices are deliberately coarser than any author mesh. Integrals
    # over them are meaningful on graded/different meshes, unlike raw cell means.
    return str(min(3,max(0,int((x+.1)/.05))))+'_'+str(min(1,max(0,int((z+.05)/.05))))

def _mean(values,volumes):
    return math.fsum(v*w for v,w in zip(values,volumes))/math.fsum(volumes)

def wall_heat_observations(artifacts, end=100.0):
    """Independently area-integrate native wallHeatFlux and contact temperatures.

    OpenFOAM's positive wallHeatFlux is heat ENTERING a region. Both the field
    and geometry are isolated native artifacts. Log integrals are a redundant
    cross-check, not a substitute for missing fields.
    """
    from .free_mesh_flow import native_boundary_area_vectors
    regions={}
    for region in EDGE_REGIONS:
        mesh={f'mesh/{name}':artifacts[f'mesh/{region}/{name}']
              for name in ('points','faces','boundary')}
        areas=native_boundary_area_vectors(mesh)
        qtree=read(artifacts[_field_path(artifacts,'wallHeatFlux',end,region)])
        ttree=read(artifacts[_field_path(artifacts,'T',end,region)])
        header=qtree.get('FoamFile',{})
        if (header.get('object')!=('wallHeatFlux',) or header.get('class')!=('volScalarField',)
                or header.get('format')!=('ascii',)
                or canonical(qtree['dimensions'])!=canonical(read('d [1 0 -3 0 0 0 0];')['d'])):
            raise ValueError('Native wall heat flux dimensions/header invalid')
        parts=header.get('location',('',))[0].strip('"').split('/')
        if len(parts)!=2 or parts[1]!=region or abs(number(parts[0])-end)>1e-7:
            raise ValueError('Native wall heat flux location invalid')
        if set(areas)!=set(qtree['boundaryField']):
            raise ValueError('Heat flux boundaries differ from native mesh')
        result={}
        for patch,vectors in areas.items():
            weights=[math.hypot(*row) for row in vectors]
            if not weights:
                continue
            qvalues=_array(qtree['boundaryField'][patch]['value'],count=len(weights))
            temperature=ttree['boundaryField'][patch].get('value')
            tvalues=_array(temperature,count=len(weights)) if temperature else None
            result[patch]={'area_m2':math.fsum(weights),
                'heat_into_region_W':math.fsum(q*a for q,a in zip(qvalues,weights)),
                'temperature_area_mean_K':_mean(tvalues,weights) if tvalues else None}
        regions[region]=result
    pairs={}
    for region,patches in regions.items():
        for patch,data in patches.items():
            if '_to_' not in patch:
                continue
            origin,other=patch.split('_to_',1)
            if origin!=region or other not in regions:
                raise ValueError('Unrecognized native material interface')
            reverse=other+'_to_'+region
            if reverse not in regions[other]:
                raise ValueError('Unpaired native material interface')
            mirror=regions[other][reverse]
            if not math.isclose(data['area_m2'],mirror['area_m2'],rel_tol=1e-8,abs_tol=1e-13):
                raise ValueError('Paired material interface areas differ')
            if region<other:
                q1,q2=data['heat_into_region_W'],mirror['heat_into_region_W']
                pairs[region+'__'+other]={'sum_into_both_W':q1+q2,
                    'relative_imbalance':abs(q1+q2)/max(abs(q1),abs(q2),1e-9)}
    hot=regions['heater']['heater_to_leftSolid']
    cold=regions['leftSolid']['leftSolid_to_heater']
    if hot['temperature_area_mean_K'] is None or cold['temperature_area_mean_K'] is None:
        raise ValueError('Contact temperatures not recorded')
    jump=hot['temperature_area_mean_K']-cold['temperature_area_mean_K']
    predicted=hot['area_m2']*jump/2.0  # one 0.001 m / 0.0005 W m^-1 K^-1 layer
    outward=-hot['heat_into_region_W']
    contact={'temperature_jump_K':jump,'area_m2':hot['area_m2'],
             'predicted_heater_to_left_W':predicted,'observed_heater_to_left_W':outward,
             'relative_law_error':abs(predicted-outward)/max(abs(predicted),1e-9)}
    return {'regions':regions,'interface_pairs':pairs,'contact':contact,
            'heater_external_input_W':regions['heater']['minY']['heat_into_region_W'],
            'energy_balance_status':'interface_and_contact_only_not_global_transient_balance'}

def _gradient(artifacts, name, count, end, size, region=''):
    """Literal registered gradient fields, including OpenFOAM tensor ordering."""
    text=artifacts[_field_path(artifacts,'grad('+name+')',end,region)]
    tree=read(text);header=tree.get('FoamFile',{})
    location=header.get('location',('',))[0].strip('"').split('/')
    if (header.get('class')!=(('volTensorField',) if size==9 else ('volVectorField',))
            or header.get('object') not in ((f'grad({name})',),('grad','(',name,')'))
            or header.get('format')!=('ascii',)
            or len(location)!=(2 if region else 1)
            or (region and location[1]!=region)
            or abs(number(location[0])-end)>1e-7):
        raise ValueError('Native gradient header mismatch')
    expected='[0 0 -1 0 0 0 0]' if name=='U' else '[0 -1 0 1 0 0 0]'
    if canonical(tree['dimensions'])!=canonical(read('d '+expected+';')['d']):
        raise ValueError('Native gradient dimensions mismatch')
    value=tree['internalField']
    kind='List<tensor>' if size==9 else 'List<vector>'
    if value[:1]==('uniform',):
        rows=[list_values(value[1:])]*count
    elif value[:2]==('nonuniform',kind) and number(value[2])==count:
        rows=list_values(value[3:])
    else:
        raise ValueError('Native gradient internal list mismatch')
    if len(rows)!=count or any(not isinstance(row,list) or len(row)!=size for row in rows):
        raise ValueError('Native gradient component/count mismatch')
    return [[number(v) for v in row] for row in rows],tree

def _previous_time(artifacts,end,field):
    times=[number(name.split('/')[0]) for name in artifacts
           if re.fullmatch(r'[0-9.eE+\-]+/'+re.escape(field),name)
           and 0<number(name.split('/')[0])<end-1e-7]
    if not times:
        raise ValueError('Energy balance requires an earlier native field from the SAME operation')
    return max(times)

def thermal_transport_balance(artifacts, observed=None):
    """s-203 rho Cp dT/dt + advection = conduction + native viscous source.

    Uses the exact constitutive source in fv::viscousDissipation: minus
    devRhoReff:grad(U), not pressure-drop or residual proxies. A finite-window
    time derivative is explicit and still needs a shorter-window author control.
    """
    from .free_mesh_flow import native_boundary_area_vectors
    observed=observed or snapshot(artifacts,'s-203')
    current=observed['regions'][''];volumes=current['volumes'];n=len(volumes);end=1.5
    before=_previous_time(artifacts,end,'T')
    previous=field_values(artifacts[_field_path(artifacts,'T',before)],'T',n,DIMENSIONS['T'],before)
    storage=1.2*1000*math.fsum((a-b)*v for a,b,v in zip(current['T'],previous,volumes))/(end-before)
    gradient,_=_gradient(artifacts,'U',n,end,9)
    _,tgrad=_gradient(artifacts,'T',n,end,3)
    source=[]
    for temp,nut,g in zip(current['T'],current['nut'],gradient):
        # Tensor components are xx,xy,xz,yx,yy,yz,zx,zy,zz. Symmetric
        # contraction is invariant if the gradient convention is transposed.
        matrix=[g[0:3],g[3:6],g[6:9]];trace=matrix[0][0]+matrix[1][1]+matrix[2][2]
        contraction=math.fsum((matrix[i][j]+matrix[j][i]-(2*trace/3 if i==j else 0))
                             *matrix[i][j] for i in range(3) for j in range(3))
        nu=15e-6*math.exp(-.1*(temp-300))
        source.append(1.2*(nu+nut)*contraction)
    dissipation=math.fsum(s*v for s,v in zip(source,volumes))
    areas=native_boundary_area_vectors(artifacts)
    nut_tree=read(artifacts[_field_path(artifacts,'nut',end)])
    conduction={}
    for name,vectors in areas.items():
        count=len(vectors)
        if not count:
            conduction[name]=0.;continue
        grad=_array(tgrad['boundaryField'][name]['value'],vector=True,count=count)
        turb=_array(nut_tree['boundaryField'][name]['value'],count=count)
        # energyTransport defaults to Prt=1.0 in this explicit physical recipe.
        conduction[name]=math.fsum((.0257+1.2*1000*nt)*sum(a*b for a,b in zip(g,sf))
                                   for nt,g,sf in zip(turb,grad,vectors))
    advection=math.fsum(observed['fluxes']['']['sensible_enthalpy_outflow_W'].values())
    rhs=dissipation+math.fsum(conduction.values())
    imbalance=storage+advection-rhs
    relative=abs(imbalance)/max(abs(rhs),abs(storage)+abs(advection),1e-9)
    return {'window_s':[before,end], 'storage_rate_W':storage,
            'net_enthalpy_outflow_W':advection,'conductive_input_W':conduction,
            'viscous_dissipation_W':dissipation,'balance_error_W':imbalance,
            'relative_balance_error':relative,
            'passed':relative<=.05,
            'qualification_note':'Candidate 5% balance gate; shorter-window convergence is additionally required.'}

def conjugate_energy_balance(artifacts, observed=None):
    """CHT total energy includes kinetic, pressure-work and gravity terms."""
    from .free_mesh_flow import native_boundary_area_vectors
    observed=observed or snapshot(artifacts,'s-202');end=100.0
    previous=_previous_time(artifacts,end,'heater/T')
    heat=wall_heat_observations(artifacts,end)
    storage_terms={};advective=0.;gravity=0.;mass={};opening_conduction={}
    for region,current in observed['regions'].items():
        volume=current['volumes'];n=len(volume)
        def old(name):
            return field_values(artifacts[_field_path(artifacts,name,previous,region)],name,n,
                                DIMENSIONS[name],previous,region=region)
        t0=old('T');t=current['T']
        if region in ('bottomWater','topAir'):
            p,p0=current['p'],old('p');u,u0=current['U'],old('U')
            cp=4181. if region=='bottomWater' else 1000.
            rho=([1000.]*n if region=='bottomWater' else [a*28.9/(8314.46261815324*b) for a,b in zip(p,t)])
            rho0=([1000.]*n if region=='bottomWater' else [a*28.9/(8314.46261815324*b) for a,b in zip(p0,t0)])
            e=[d*(cp*(tt-300)+.5*sum(a*a for a in vv))-pp for d,tt,vv,pp in zip(rho,t,u,p)]
            e0=[d*(cp*(tt-300)+.5*sum(a*a for a in vv))-pp for d,tt,vv,pp in zip(rho0,t0,u0,p0)]
            gravity+=math.fsum(d*(-9.81)*vv[1]*v for d,vv,v in zip(rho,u,volume))
            flux=observed['fluxes'][region]
            advective+=math.fsum(flux['sensible_enthalpy_outflow_W'].values())
            phi=read(artifacts[_field_path(artifacts,'phi',end,region)])
            velocity=read(artifacts[_field_path(artifacts,'U',end,region)])
            ctree=read(artifacts[_field_path(artifacts,'C',end,region)])
            for name,bc in phi['boundaryField'].items():
                cvalue=ctree['boundaryField'][name].get('value',())
                nfaces=len(_array(cvalue,vector=True)) if cvalue[:1]==('nonuniform',) else None
                q=_array(bc['value'],count=nfaces)
                if not any(v!=0 for v in q):
                    continue
                uv=_array(velocity['boundaryField'][name]['value'],vector=True,count=len(q))
                advective+=math.fsum(f*.5*sum(a*a for a in vv) for f,vv in zip(q,uv))
            rate=math.fsum((a-b)*v for a,b,v in zip(rho,rho0,volume))/(end-previous)
            net=math.fsum(flux['boundary_flux'].values())
            mass[region]={'storage_kg_s':rate,'net_outflow_kg_s':net,
                          'error_kg_s':rate+net}
            # wallHeatFlux excludes non-wall inlets/outlets. Their fixed-T
            # conductive input must not silently disappear from total energy.
            _,grad_t=_gradient(artifacts,'T',n,end,3,region)
            mesh={f'mesh/{key}':artifacts[f'mesh/{region}/{key}']
                  for key in ('points','faces','boundary')}
            area=native_boundary_area_vectors(mesh)
            kappa=959e-6*4181/6.62 if region=='bottomWater' else 1.8e-5*1000/.7
            opening_conduction[region]={}
            for patch in ('minX','maxX'):
                vectors=area[patch]
                g=_array(grad_t['boundaryField'][patch]['value'],vector=True,count=len(vectors))
                opening_conduction[region][patch]=kappa*math.fsum(
                    sum(a*b for a,b in zip(row,sf)) for row,sf in zip(g,vectors))
        else:
            e=[8000*450*(v-300) for v in t];e0=[8000*450*(v-300) for v in t0]
        storage_terms[region]=math.fsum((a-b)*v for a,b,v in zip(e,e0,volume))/(end-previous)
    # Paired internal fluxes should cancel; only exterior wall heating belongs
    # in the global RHS. Report their independent inconsistency separately.
    external=math.fsum(v['heat_into_region_W'] for r in heat['regions'].values()
                      for patch,v in r.items() if '_to_' not in patch)
    storage=math.fsum(storage_terms.values())
    opening_heat=math.fsum(v for patches in opening_conduction.values() for v in patches.values())
    error=storage+advective-external-opening_heat-gravity
    relative=abs(error)/max(abs(external)+abs(opening_heat)+abs(gravity),abs(storage)+abs(advective),1e-9)
    contact=heat['contact']['relative_law_error']
    pair=max(row['relative_imbalance'] for row in heat['interface_pairs'].values())
    return {'window_s':[previous,end], 'storage_rate_W':storage_terms,
        'enthalpy_and_kinetic_outflow_W':advective,'external_wall_input_W':external,
        'opening_conductive_input_W':opening_conduction,
        'gravity_power_W':gravity,'global_error_W':error,'relative_balance_error':relative,
        'mass_balance':mass,'wall_heat':heat,
        'passed':relative<=.05 and pair<=.05 and contact<=.05,
        'qualification_note':'Spatial, time-window and coupling convergence must all be demonstrated.'}

@native_output_reader
def snapshot(artifacts, task_id, *, require_flux=True):
    _check_task(task_id)
    end=100.0 if task_id=='s-202' else 1.5
    log=artifacts.get('solver.log','')
    if not ExecutionSpec((),'transient',end,1e-7,False,(),300).completed(log):
        raise ValueError('Real terminal time not proven')
    last=log[list(re.finditer(r'^Time = ',log,re.M))[-1].end():]
    if task_id=='s-203' and 'Solving for T,' not in last:
        raise ValueError('Temperature equation did not execute at terminal time')
    residual_name='p_rgh' if task_id=='s-202' else 'p'
    residuals=re.findall(r'Solving for '+residual_name+r', Initial residual = ([^, ]+), Final residual = ([^, ]+)',last)
    if not residuals:
        raise ValueError('Terminal pressure residual missing')
    initial,final=map(number,residuals[-1])
    if min(initial,final)<0:
        raise ValueError('Negative residual')
    measures={'final_time':{'unit':'s','value':end},
        'pressure_initial_residual':{'unit':'1','value':initial},
        'pressure_final_residual':{'unit':'1','value':final}}
    blocks={}; all_fields={}; fluxes={}
    for region in REGIONS[task_id]:
        prefix=(region+'_') if region else ''
        ctext=artifacts[_field_path(artifacts,'C',end,region)]
        ctokens=read(ctext).get('internalField',())
        if ctokens[:2]!=('nonuniform','List<vector>'):
            raise ValueError('Native cell centres must be explicit')
        count=number(ctokens[2])
        if not count.is_integer():
            raise ValueError('Native cell count not an integer')
        count=int(count)
        def field(name):
            dim='[0 2 -2 0 0 0 0]' if task_id=='s-203' and name=='p' else DIMENSIONS[name]
            return field_values(artifacts[_field_path(artifacts,name,end,region)],name,count,dim,end,
                                region=region or None)
        c,v,t=field('C'),field('V'),field('T')
        if any(w<=0 for w in v) or any(temp<=0 for temp in t):
            raise ValueError('Nonpositive native volume or temperature')
        total=math.fsum(v)
        if not math.isclose(total,VOLUMES[region],rel_tol=1e-7,abs_tol=1e-13):
            raise ValueError('Native material/domain volume differs from geometry')
        names=['T']
        fluid=region in ('','bottomWater','topAir')
        if fluid:
            names+=['U','p']+(['p_rgh'] if region else ['k','epsilon','nut'])
        values={name:field(name) for name in names}
        # Only ideal-gas absolute pressure must be positive. Constant-density
        # water and incompressible kinematic pressure permit gauge zero/negative.
        if region=='topAir' and min(values['p'])<=0:
            raise ValueError('Ideal-gas absolute pressure must be positive')
        if any(min(values[name]) < -1e-10 for name in ('k','epsilon','nut') if name in values):
            raise ValueError('Negative turbulence quantity')
        bins={}
        for i,point in enumerate(c):
            key=spatial_bin(task_id,region,point)
            bins.setdefault(key,[]).append(i)
        projected={}
        for key,indices in sorted(bins.items()):
            weights=[v[i] for i in indices]
            projected[key]={'volume':math.fsum(weights)}
            for name,data in values.items():
                projected[key][name]=([_mean([data[i][j] for i in indices],weights) for j in range(3)]
                    if name=='U' else _mean([data[i] for i in indices],weights))
        blocks[region]=projected
        all_fields[region]={'centres':c,'volumes':v,**values}
        for name,unit,value in [('cell_count','1',count),('volume','m3',total),
            ('T_volume_mean','K',_mean(t,v)),('T_min_max','K',[min(t),max(t)]),
            ('T_rise_rms','K',math.sqrt(_mean([(x-300)**2 for x in t],v)))]:
            measures[prefix+name]={'unit':unit,'value':value}
        if fluid:
            u=values['U']
            measures[prefix+'U_volume_mean']={'unit':'m/s','value':[_mean([q[j] for q in u],v) for j in range(3)]}
            measures[prefix+'speed_volume_rms']={'unit':'m/s','value':math.sqrt(_mean([sum(a*a for a in q) for q in u],v))}
            if require_flux:
                flux=flux_observations(artifacts,task_id,end,region)
                fluxes[region]=flux
                openings=('minX','maxX') if region else ('inlet','outlet1','outlet2')
                for name in openings:
                    measures[prefix+name+'_flow']={'unit':flux['unit'],'value':flux['boundary_flux'][name]}
                    measures[prefix+name+'_enthalpy_flux']={'unit':'W','value':flux['sensible_enthalpy_outflow_W'][name]}
        if task_id=='s-203':
            # 315 K is the entering temperature: viscous heating is only about
            # hundredths of a kelvin and must not be hidden by a 300 K offset.
            measures['temperature_excess_315K']={'unit':'K','value':_mean([x-315 for x in t],v)}
            measures['relative_300K_sensible_enthalpy']={'unit':'J','value':1.2*1000*math.fsum((x-300)*w for x,w in zip(t,v))}
        else:
            rho=[1000.0]*count if region=='bottomWater' else (
                [p*28.9/(8314.46261815324*temp) for p,temp in zip(values['p'],t)] if region=='topAir'
                else [8000.0]*count)
            cp=4181.0 if region=='bottomWater' else 1000.0 if region=='topAir' else 450.0
            measures[prefix+'relative_300K_sensible_enthalpy']={'unit':'J',
                'value':math.fsum(d*cp*(temp-300)*w for d,temp,w in zip(rho,t,v))}
    return {'version':VERSION,'task_id':task_id,'measurements':measures,
            'spatial_volumes':blocks,'regions':all_fields,'fluxes':fluxes,
            'energy_balance_status':'not_proven_by_endpoint_storage_or_boundary_flux_alone'}

def measurement_schema(task_id):
    result={'final_time':('s',1),'pressure_initial_residual':('1',1),'pressure_final_residual':('1',1)}
    for region in REGIONS[task_id]:
        prefix=region+'_' if region else ''
        for name,unit,size in [('cell_count','1',1),('volume','m3',1),('T_volume_mean','K',1),
            ('T_min_max','K',2),('T_rise_rms','K',1),('relative_300K_sensible_enthalpy','J',1)]:
            result[prefix+name]=(unit,size)
        if region in ('','bottomWater','topAir'):
            result[prefix+'U_volume_mean']=('m/s',3)
            result[prefix+'speed_volume_rms']=('m/s',1)
            for name in (('minX','maxX') if region else ('inlet','outlet1','outlet2')):
                result[prefix+name+'_flow']=('kg/s' if region else 'm3/s',1)
                result[prefix+name+'_enthalpy_flux']=('W',1)
    if task_id=='s-203':
        result['temperature_excess_315K']=('K',1)
    return result

def compare_spatial(left,right):
    """Diagnostic dimensional norms; a separate reviewed policy sets thresholds."""
    if set(left)!=set(right):
        raise ValueError('Different physical regions')
    out={}
    for region in left:
        a,b=left[region],right[region]
        if set(a)!=set(b):
            raise ValueError('Physical observation volume absent on candidate mesh')
        for field in sorted(set(next(iter(b.values())))-{'volume'}):
            errors=[]; scale=[]; weights=[]
            for key in b:
                aa,bb=a[key][field],b[key][field]
                av,bv=aa if isinstance(aa,list) else [aa],bb if isinstance(bb,list) else [bb]
                if len(av)!=len(bv):
                    raise ValueError('Field component mismatch')
                weights.extend([b[key]['volume']]*len(av))
                errors.extend((x-y)**2 for x,y in zip(av,bv))
                offset=300.0 if field=='T' else 0.0
                scale.extend((v-offset)**2 for v in bv)
            rms=math.sqrt(_mean(errors,weights)); ref=math.sqrt(_mean(scale,weights))
            out[(region+'/' if region else '')+field]={'rms_difference':rms,'reference_rms':ref,
                'relative_rms':rms/ref if ref>1e-14 else None}
    return out
