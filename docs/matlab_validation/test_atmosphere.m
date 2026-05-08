% test_atmosphere.m — Phase 2.5 cross-validation (Octave base only).
%
% Verifies ISA standard atmosphere + ITU-R P.838 simplified rain
% attenuation against the Python implementation in
% src/workbench/physics/atmosphere.py.
%
% No Toolbox calls. Pure base math.

function test_atmosphere
    % --- ISA constants ---
    L = 0.0065;
    R = 287.058;
    g = 9.80665;
    T0 = 288.15;
    P0 = 101325.0;
    exponent = g / (R * L);

    % @ sea level
    rho0 = P0 / (R * T0);
    expect_close('rho_0', rho0, 1.225, 1e-3);

    % @ 1000 m
    T1 = T0 - L * 1000;
    P1 = P0 * (T1 / T0)^exponent;
    rho1 = P1 / (R * T1);
    expect_close('T_1km', T1, 281.65, 1e-9);
    expect_close('P_1km', P1, 89874.7555, 1e-3);
    expect_close('rho_1km', rho1, 1.111625, 1e-5);

    % @ 11 km (tropopause)
    T11 = T0 - L * 11000;
    P11 = P0 * (T11 / T0)^exponent;
    rho11 = P11 / (R * T11);
    printf('rho @ 11 km = %.6f kg/m^3\n', rho11);

    % --- Rain attenuation (X-band, 9.4 GHz, 10 mm/h) ---
    f = 9.4;
    R_rate = 10.0;
    k = 0.0117 * f - 0.0734;
    alpha = 1.097;
    L_dbkm = k * (R_rate^alpha);
    expect_close('rain_L_xband', L_dbkm, 0.457345, 1e-5);

    % Two-way @ 100 km
    two_way = 2 * 100 * L_dbkm;
    expect_close('two_way_100km', two_way, 91.468951, 1e-4);

    printf('PASS\n');
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.9f, expected %.9f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.9f\n', name, actual);
    end
end
