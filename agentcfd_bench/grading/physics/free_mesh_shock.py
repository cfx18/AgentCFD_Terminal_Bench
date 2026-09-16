"""Pure numeric extraction/comparison migrated from free_mesh_shock; no runtime policy."""
from dataclasses import dataclass
import math
import re
from .evaluation import native_output_reader
from .foam.parsed import read
from .foam.science_metrics import field_values, number

GAS_R = 8314.46261815324 / 28.96

CP = 1004.5

GAMMA = CP / (CP - GAS_R)

END = .007

BINS = 40

BOUNDS = (-5., 5.)

AREA = 4.

UNITS = {'rho': 'kg/m3', 'p': 'Pa', 'T': 'K', 'Ux': 'm/s'}

DIMENSIONS = {'C':'[0 1 0 0 0 0 0]', 'V':'[0 3 0 0 0 0 0]',
              'U':'[0 1 -1 0 0 0 0]', 'p':'[1 -1 -2 0 0 0 0]',
              'T':'[0 0 0 1 0 0 0]', 'rho':'[1 -3 0 0 0 0 0]'}

SCHEMA = {'final_time':('s',1), 'cell_count':('1',1), 'volume':('m3',1),
          'mass':('kg',1), 'axial_momentum':('kg m/s',1),
          'total_energy':('J',1), 'U_volume_mean':('m/s',3),
          'transverse_velocity_rms':('m/s',1),
          'last_initial_residual':('1',1), 'last_final_residual':('1',1),
          **{f'{name}_axial_bin_mean':(unit,BINS) for name,unit in UNITS.items()}}

@dataclass(frozen=True)
class State:
    rho: float
    u: float
    p: float

class RiemannSolution:
    """Positive-pressure, non-vacuum ideal Euler solution; bounded bisection."""
    def __init__(self, left, right, gamma=GAMMA):
        if (not math.isfinite(gamma) or gamma<=1 or any(
                not math.isfinite(v) for state in (left,right)
                for v in (state.rho,state.u,state.p))
                or min(left.rho,right.rho,left.p,right.p)<=0):
            raise ValueError('Finite positive Riemann states and gamma>1 required')
        self.left,self.right,self.gamma=left,right,gamma
        self.cl=math.sqrt(gamma*left.p/left.rho)
        self.cr=math.sqrt(gamma*right.p/right.rho)
        if right.u-left.u>=2*(self.cl+self.cr)/(gamma-1):
            raise ValueError('Vacuum Riemann problem is outside this task')
        def f(p,state,c):
            if p>state.p:
                return (p-state.p)*math.sqrt(2/((gamma+1)*state.rho)/
                    (p+(gamma-1)/(gamma+1)*state.p))
            return 2*c/(gamma-1)*((p/state.p)**((gamma-1)/(2*gamma))-1)
        def balance(p): return f(p,left,self.cl)+f(p,right,self.cr)+right.u-left.u
        lo,hi=0.,max(left.p,right.p)
        for _ in range(100):
            if balance(hi)>=0: break
            hi*=2
        else: raise ValueError('Riemann pressure bracket not found')
        for _ in range(120):
            mid=(lo+hi)/2
            if balance(mid)>0: hi=mid
            else: lo=mid
        self.pstar=(lo+hi)/2
        self.ustar=.5*(left.u+right.u+f(self.pstar,right,self.cr)-f(self.pstar,left,self.cl))
        ratio=(gamma-1)/(gamma+1)
        def star(state):
            r=self.pstar/state.p
            return state.rho*((r+ratio)/(ratio*r+1) if r>1 else r**(1/gamma))
        self.rhol,self.rhor=star(left),star(right)
        self.clstar=math.sqrt(gamma*self.pstar/self.rhol)
        self.crstar=math.sqrt(gamma*self.pstar/self.rhor)
        self.sl=left.u-self.cl*math.sqrt((gamma+1)/(2*gamma)*self.pstar/left.p+(gamma-1)/(2*gamma))
        self.sr=right.u+self.cr*math.sqrt((gamma+1)/(2*gamma)*self.pstar/right.p+(gamma-1)/(2*gamma))
        self.speeds=sorted(set([
            self.sl if self.pstar>left.p else left.u-self.cl,
            self.sl if self.pstar>left.p else self.ustar-self.clstar,
            self.ustar,
            self.sr if self.pstar>right.p else self.ustar+self.crstar,
            self.sr if self.pstar>right.p else right.u+self.cr]))

    def at(self,x,t=END):
        if not math.isfinite(x) or not math.isfinite(t) or t<0:
            raise ValueError('Finite coordinate/nonnegative time required')
        if t==0: return self.left if x<0 else self.right
        s=x/t; g=self.gamma
        if s<=self.ustar:
            state=self.left
            if self.pstar>state.p:
                return state if s<self.sl else State(self.rhol,self.ustar,self.pstar)
            if s<=state.u-self.cl: return state
            if s>=self.ustar-self.clstar: return State(self.rhol,self.ustar,self.pstar)
            u=2/(g+1)*(self.cl+(g-1)/2*state.u+s)
            c=2/(g+1)*(self.cl+(g-1)/2*(state.u-s))
            return State(state.rho*(c/self.cl)**(2/(g-1)),u,state.p*(c/self.cl)**(2*g/(g-1)))
        state=self.right
        if self.pstar>state.p:
            return state if s>self.sr else State(self.rhor,self.ustar,self.pstar)
        if s>=state.u+self.cr: return state
        if s<=self.ustar+self.crstar: return State(self.rhor,self.ustar,self.pstar)
        u=2/(g+1)*(-self.cr+(g-1)/2*state.u+s)
        c=2/(g+1)*(self.cr-(g-1)/2*(state.u-s))
        return State(state.rho*(c/self.cr)**(2/(g-1)),u,state.p*(c/self.cr)**(2*g/(g-1)))

    def average(self,a,b,t=END):
        if not (math.isfinite(a) and math.isfinite(b) and a<b):
            raise ValueError('Nonempty finite cell interval required')
        # Eight-point Gauss-Legendre on each smooth piece; discontinuities are
        # explicit integration boundaries, never hidden behind point sampling.
        nodes=(.1834346424956498,.5255324099163290,.7966664774136267,.9602898564975363)
        weights=(.3626837833783620,.3137066458778873,.2223810344533745,.1012285362903763)
        cuts=sorted(set([a,b,*[v*t for v in self.speeds if a<v*t<b]]))
        result=dict.fromkeys(UNITS,0.)
        for low,high in zip(cuts,cuts[1:]):
            mid,half=(low+high)/2,(high-low)/2
            for node,weight in zip(nodes,weights):
                for sign in (-1,1):
                    q=self.at(mid+sign*half*node,t)
                    for name,value in {'rho':q.rho,'p':q.p,'T':q.p/(GAS_R*q.rho),'Ux':q.u}.items():
                        result[name]+=half*weight*value/(b-a)
        return result

def solution():
    return RiemannSolution(State(100000/(GAS_R*348.432),0.,100000.),
                           State(10000/(GAS_R*278.746),0.,10000.))

def field_at(artifacts,name,end):
    matches=[path for path in artifacts if re.fullmatch(r'[0-9.eE+\-]+/'+re.escape(name),path)
             and abs(number(path.split('/')[0])-end)<1e-7]
    if len(matches)!=1: raise ValueError('Missing/ambiguous actual native field: '+name)
    return artifacts[matches[0]]

def native_fields(artifacts,end,dimensions):
    ctext=field_at(artifacts,'C',end)
    internal=read(ctext).get('internalField',())
    if len(internal)<3 or internal[:2]!=('nonuniform','List<vector>'):
        raise ValueError('Explicit native cell-centre list required')
    n=number(internal[2])
    if not n.is_integer() or not 0<n<=1000000: raise ValueError('Invalid native cell count')
    n=int(n)
    fields={name:field_values(field_at(artifacts,name,end),name,n,dim,end)
            for name,dim in dimensions.items()}
    if any(v<=0 for v in fields['V']): raise ValueError('Nonpositive native cell volume')
    return fields

def axial_cells(centres,volumes):
    cells=sorted((c[0]-v/(2*AREA),c[0]+v/(2*AREA),i) for i,(c,v) in enumerate(zip(centres,volumes)))
    if (not cells or any(abs(c[1])>1e-8 or abs(c[2])>1e-8 for c in centres)
            or abs(cells[0][0]-BOUNDS[0])>1e-6 or abs(cells[-1][1]-BOUNDS[1])>1e-6
            or any(abs(a[1]-b[0])>1e-6 for a,b in zip(cells,cells[1:]))):
        raise ValueError('Native mesh must tile the supplied 1D tube without gaps/overlap')
    return cells

def rebin(cells,values,bins=BINS):
    width=(BOUNDS[1]-BOUNDS[0])/bins
    result=[]
    for j in range(bins):
        a,b=BOUNDS[0]+j*width,BOUNDS[0]+(j+1)*width
        result.append(math.fsum(max(0.,min(b,hi)-max(a,lo))*values[i]
                               for lo,hi,i in cells)/width)
    return result

@native_output_reader
def snapshot(artifacts):
    from .completion import Completion as ExecutionSpec
    log=artifacts.get('solver.log','')
    if not ExecutionSpec((),'transient',END,1e-7,False,(),300).completed(log):
        raise ValueError('Actual final solver time not proven')
    data=native_fields(artifacts,END,DIMENSIONS)
    cells=axial_cells(data['C'],data['V'])
    volume=math.fsum(data['V'])
    def mean(values): return math.fsum(a*b for a,b in zip(values,data['V']))/volume
    last=log[list(re.finditer(r'^Time = ',log,re.M))[-1].start():]
    residuals=re.findall(r'Solving for rhoE, Initial residual = ([^,\s]+), Final residual = ([^,\s]+)',last)
    if not residuals: raise ValueError('Native final energy residual missing')
    initial,final=map(number,residuals[-1])
    if min(initial,final)<0: raise ValueError('Negative native residual')
    fields={name:data[name] for name in ('rho','p','T')}
    fields['Ux']=[u[0] for u in data['U']]
    energy=[p/(GAMMA-1)+.5*r*sum(x*x for x in u) for p,r,u in zip(data['p'],data['rho'],data['U'])]
    values={'final_time':END,'cell_count':len(cells),'volume':volume,
            'mass':mean(data['rho'])*volume,
            'axial_momentum':mean([r*u[0] for r,u in zip(data['rho'],data['U'])])*volume,
            'total_energy':mean(energy)*volume,
            'U_volume_mean':[mean([u[j] for u in data['U']]) for j in range(3)],
            'transverse_velocity_rms':math.sqrt(mean([u[1]**2+u[2]**2 for u in data['U']])),
            'last_initial_residual':initial,'last_final_residual':final,
            **{name+'_axial_bin_mean':rebin(cells,arr) for name,arr in fields.items()}}
    exact=solution(); errors={}
    expected=[(i,exact.average(a,b)) for a,b,i in cells]
    scales={'rho':exact.left.rho,'p':exact.left.p,'T':348.432,'Ux':exact.cl}
    for name,arr in fields.items():
        errors[name]=math.fsum(abs(arr[i]-target[name])*data['V'][i]
                              for i,target in expected)/volume/scales[name]
    measures={k:{'unit':SCHEMA[k][0],'value':v} for k,v in values.items()}
    return {'measurements':measures,'data':data,'normalized_l1':errors,
            'equation_of_state_relative_max':max(abs(p-r*GAS_R*T)/max(abs(p),1.)
                for p,r,T in zip(data['p'],data['rho'],data['T']))}
