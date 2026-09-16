"""PRIVATE qualification fixture, not a starter case and never mounted for agents."""


def header(name, kind='dictionary'):
    return f'FoamFile {{ version 2.0; format ascii; class {kind}; object {name}; }}\n'


MESH_BOUNDARY = '''
left { type cyclic; neighbourPatch right; faces ((0 4 7 3)); }
right { type cyclic; neighbourPatch left; faces ((1 2 6 5)); }
bottom { type wall; faces ((0 1 5 4)); }
top { type wall; faces ((3 7 6 2)); }
frontAndBack { type empty; faces ((0 3 2 1) (4 5 6 7)); }
'''


def reference_files():
    return {
        'system/controlDict': header('controlDict') + '''
application icoFoam; startFrom startTime; startTime 0; stopAt endTime; endTime 2;
deltaT 0.005; writeControl runTime; writeInterval 2; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off; timeFormat general;
timePrecision 12; runTimeModifiable false;
''',
        'system/blockMeshDict': header('blockMeshDict') + '''
scale 1;
vertices ((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 0.1) (1 0 0.1) (1 1 0.1) (0 1 0.1));
blocks (hex (0 1 2 3 4 5 6 7) (4 20 1) simpleGrading (1 1 1));
edges (); boundary (''' + MESH_BOUNDARY + '''); mergePatchPairs ();
''',
        'constant/transportProperties': header('transportProperties') + 'nu [0 2 -1 0 0 0 0] 0.1;\n',
        '0/U': header('U', 'volVectorField') + '''
dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {
top { type fixedValue; value uniform (1 0 0); }
bottom { type fixedValue; value uniform (0 0 0); }
left { type cyclic; } right { type cyclic; } frontAndBack { type empty; }
}
''',
        '0/p': header('p', 'volScalarField') + '''
dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {
top { type zeroGradient; } bottom { type zeroGradient; }
left { type cyclic; } right { type cyclic; } frontAndBack { type empty; }
}
''',
        'system/fvSchemes': header('fvSchemes') + '''
ddtSchemes { default Euler; } gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; } snGradSchemes { default corrected; }
''',
        'system/fvSolution': header('fvSolution') + '''
solvers {
p { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0; }
pFinal { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0; }
U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0; }
}
PISO { nCorrectors 2; nNonOrthogonalCorrectors 0; pRefCell 0; pRefValue 0; }
''',
    }
