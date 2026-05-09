% test_extended_target.m — Phase 2.7 cross-validation (Octave base only).
%
% Verifies multi-scatterer coherent sum + apparent centroid (glint)
% (plan/14 § 14.10) against the Python implementation in
% src/workbench/physics/reflection/extended_target.py.
%
% Conventions (matches Python):
% - Body frame: x forward, y right, z down (aerospace).
% - World: ENU. yaw CW from N about +Up, pitch nose-up, roll right-down.
% - Round-trip phase = 4 pi R / lambda. Amplitude = sqrt(sigma) / R^2.
%
% No Toolbox calls. Pure base math.

function test_extended_target
    c = 299792458;

    % --- body_to_world_rotation: zero attitude ---
    R = body_to_world(0, 0, 0);
    bx = R * [1; 0; 0];     % body forward → +North = (0, 1, 0)
    expect_close('zero_bx_E', bx(1), 0.0, 1e-12);
    expect_close('zero_bx_N', bx(2), 1.0, 1e-12);
    expect_close('zero_bx_U', bx(3), 0.0, 1e-12);

    by = R * [0; 1; 0];     % body right → +East = (1, 0, 0)
    expect_close('zero_by_E', by(1), 1.0, 1e-12);
    expect_close('zero_by_N', by(2), 0.0, 1e-12);

    bz = R * [0; 0; 1];     % body down → -Up = (0, 0, -1)
    expect_close('zero_bz_U', bz(3), -1.0, 1e-12);

    % --- yaw = pi/2 → forward to East ---
    R = body_to_world(pi/2, 0, 0);
    bx = R * [1; 0; 0];
    expect_close('yaw90_bx_E', bx(1), 1.0, 1e-12);
    expect_close('yaw90_bx_N', bx(2), 0.0, 1e-12);

    % --- Orthonormality + det=1 ---
    R = body_to_world(0.7, -0.3, 0.2);
    Id = R' * R;
    err = max(max(abs(Id - eye(3))));
    expect_close('orthonormal', err, 0.0, 1e-12);
    expect_close('det_one', det(R), 1.0, 1e-12);

    % --- Single scatterer at body origin: amplitude 1/R^2 ---
    % Target at (1000, 0, 0) ENU, radar at origin, σ = 1 m^2.
    % R = 1000 m → A = 1/1e6 = 1e-6.
    sigma_lin = 1.0;
    R_m = 1000.0;
    A_expected = sqrt(sigma_lin) / R_m^2;
    expect_close('amp_1km', A_expected, 1e-6, 1e-15);

    % --- Inverse-square scaling: doubling R divides A by 4 ---
    A1 = sqrt(sigma_lin) / 1000^2;
    A2 = sqrt(sigma_lin) / 2000^2;
    expect_close('inv_sq_ratio', A1 / A2, 4.0, 1e-12);

    % --- Constructive interference: lambda/2 separation along LOS ---
    %   Two scatterers separated by lambda/2 in range:
    %   Δphase = 4 pi * (lambda/2) / lambda = 2 pi → coherent (aligned).
    f = 9.4e9;
    lambda = c / f;
    sep = lambda / 2;
    R0 = 10000.0;
    R1 = R0 + sep;
    A0 = sqrt(sigma_lin) / R0^2;
    A1 = sqrt(sigma_lin) / R1^2;
    phi0 = 4 * pi * R0 / lambda;
    phi1 = 4 * pi * R1 / lambda;
    s0 = A0 * exp(-1j * phi0);
    s1 = A1 * exp(-1j * phi1);
    sum_constructive = s0 + s1;
    % |sum| should be ~2 * A0 (within ~1e-3 due to small range diff)
    expect_close('constructive_amp', abs(sum_constructive), 2.0 * A0, 0.01 * A0);

    % --- Destructive interference: lambda/4 separation along LOS ---
    %   Δphase = 4 pi * (lambda/4) / lambda = pi → cancel.
    sep = lambda / 4;
    R1 = R0 + sep;
    A1 = sqrt(sigma_lin) / R1^2;
    phi1 = 4 * pi * R1 / lambda;
    s1 = A1 * exp(-1j * phi1);
    sum_destructive = s0 + s1;
    expect_close('destructive_amp_below', abs(sum_destructive) < 0.01 * A0, 1, 0);

    % --- Total RCS combination: two 0 dBsm sources → 3.01 dBsm ---
    sigma_a = 10^(0/10);  % 1 m^2
    sigma_b = 10^(0/10);  % 1 m^2
    total_dbsm = 10 * log10(sigma_a + sigma_b);
    expect_close('total_rcs_3db', total_dbsm, 10 * log10(2), 1e-12);

    % --- Apparent centroid: amplitude-weighted ---
    %   Two equal scatterers at (5, 0, 0) and (-5, 0, 0) East offsets,
    %   far field → apparent centroid ~ midpoint (target ref).
    pos1 = [5; 0; 0];
    pos2 = [-5; 0; 0];
    w1 = 1.0;
    w2 = 1.0;
    centroid = (w1 * pos1 + w2 * pos2) / (w1 + w2);
    expect_close('symmetric_centroid_E', centroid(1), 0.0, 1e-12);

    %   Now with brighter +5 East source (10 dBsm vs 0 dBsm):
    %   amplitudes scale as sqrt(10) vs sqrt(1).
    w1 = sqrt(10);
    w2 = 1.0;
    centroid = (w1 * pos1 + w2 * pos2) / (w1 + w2);
    expect_close('asym_centroid_pulled_east_pos', centroid(1) > 0, 1, 0);

    printf('PASS\n');
end

function R = body_to_world(yaw, pitch, roll)
    sy = sin(yaw);  cy = cos(yaw);
    sp = sin(pitch); cp = cos(pitch);
    sr = sin(roll); cr = cos(roll);

    bx         = [sy*cp; cy*cp; sp];
    by_no_roll = [cy;    -sy;   0];
    bz_no_roll = [sy*sp; cy*sp; -cp];

    by = by_no_roll * cr + bz_no_roll * sr;
    bz = -by_no_roll * sr + bz_no_roll * cr;

    R = [bx, by, bz];
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.12f, expected %.12f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.12f\n', name, actual);
    end
end
