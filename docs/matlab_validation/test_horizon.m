function test_horizon()
%% test_horizon.m — TRsim physics/propagation/ray_tracing.py reference values
%
% Plain MATLAB / GNU Octave (no Toolbox).
%
% Usage:
%   octave docs/matlab_validation/test_horizon.m
%
% Author: TRsim Phase 1.4 cross-validation.

    fprintf('=== TRsim physics/propagation/ray_tracing.py reference values ===\n\n');

    R_E = 6371008.7714;            % WGS84 mean radius [m]
    K   = 4/3;                     % standard atmosphere

    %% 1. Effective Earth radius
    Reff = K * R_E;
    fprintf('1. Effective Earth radius (k=4/3): %.4f m\n', Reff);
    fprintf('   Expected ≈ 8494678.36 m\n\n');

    %% 2. Horizon @ 100 m, 4/3 Earth
    h = 100;
    d_4_3 = sqrt(2 * K * R_E * h);
    fprintf('2. Horizon @ h=100m (k=4/3): %.4f m  (= %.3f km)\n', d_4_3, d_4_3/1000);
    fprintf('   Expected ≈ 41219.36 m\n\n');

    %% 3. Geometric horizon @ 100 m
    d_geo = sqrt(2 * 1 * R_E * h);
    fprintf('3. Horizon @ h=100m (k=1):   %.4f m  (= %.3f km)\n', d_geo, d_geo/1000);
    fprintf('   Expected ≈ 35696.40 m  (refraction extends LOS by ~5.5 km)\n\n');

    %% 4. Horizon table (k=4/3)
    fprintf('4. Horizon distances (k=4/3):\n');
    for h = [1, 10, 100, 1000, 10000]
        d = sqrt(2 * K * R_E * h);
        fprintf('   h=%6.0f m → %.3f km\n', h, d/1000);
    end
    fprintf('\n');

    %% 5. Radio horizon between h1=10m and h2=100m
    d_h1 = sqrt(2 * K * R_E * 10);
    d_h2 = sqrt(2 * K * R_E * 100);
    radio = d_h1 + d_h2;
    fprintf('5. Radio horizon h1=10m + h2=100m\n');
    fprintf('   horizon(10)  = %.4f m\n', d_h1);
    fprintf('   horizon(100) = %.4f m\n', d_h2);
    fprintf('   sum (radio)  = %.4f m  (= %.3f km)\n\n', radio, radio/1000);

    %% 6. Earth bulge — midpoint of 10 km segment
    bulge_mid = (5000 * 5000) / (2 * K * R_E);
    fprintf('6. Earth bulge at midpoint of 10 km (k=4/3): %.6f m\n', bulge_mid);
    fprintf('   Expected ≈ 1.4714 m\n\n');

    %% 7. Two-ray geometry — h1=10m, h2=100m, d=10km
    h1 = 10; h2 = 100; d = 10000;
    direct = sqrt(d^2 + (h2-h1)^2);
    reflected = sqrt(d^2 + (h1+h2)^2);
    delta_exact = reflected - direct;
    delta_approx = 2 * h1 * h2 / d;
    fprintf('7. Two-ray geometry (h1=10m, h2=100m, d=10km)\n');
    fprintf('   direct    = %.6f m\n', direct);
    fprintf('   reflected = %.6f m\n', reflected);
    fprintf('   Δ exact   = %.6f m\n', delta_exact);
    fprintf('   Δ approx  = %.6f m  (= 2·h1·h2/d)\n', delta_approx);
    fprintf('   rel diff  = %.3e\n\n', abs(delta_exact - delta_approx) / delta_approx);

    %% 8. Two-ray far field — d=50 km
    d = 50000;
    direct = sqrt(d^2 + (h2-h1)^2);
    reflected = sqrt(d^2 + (h1+h2)^2);
    delta_exact = reflected - direct;
    delta_approx = 2 * h1 * h2 / d;
    fprintf('8. Far field (d=50km): Δ_exact=%.6e, Δ_approx=%.6e, rel_diff=%.3e\n', ...
            delta_exact, delta_approx, abs(delta_exact - delta_approx) / delta_approx);
    fprintf('   Expected rel_diff < 1e-3 (far field 근사 유효)\n\n');

    fprintf('=== End ===\n');
end
