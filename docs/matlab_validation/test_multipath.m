function test_multipath()
%% test_multipath.m - TRsim physics/propagation/multipath.py reference values
%
% Plain MATLAB / GNU Octave (no Toolbox).
%
% Usage:
%   octave docs/matlab_validation/test_multipath.m
%
% Author: TRsim Phase 1.6 cross-validation.

    fprintf('=== TRsim physics/propagation/multipath.py reference values ===\n\n');

    C = 299792458;
    fc = 9.4e9;
    lam = C / fc;
    h1 = 10; h2 = 100;
    fprintf('X-band, h1=%.0fm, h2=%.0fm, lambda=%.6f m\n\n', h1, h2, lam);

    %% 1. Last lobing null (rho=-1, far-field): d = 2*h1*h2/lambda
    d_null = 2*h1*h2/lam;
    fprintf('1. Last null distance: d_null_1 = 2*h1*h2/lambda = %.4f m (= %.3f km)\n', ...
            d_null, d_null/1000);
    fprintf('   Expected: ~62710.05 m (~62.7 km)\n\n');

    %% 2. First lobing peak: d = 4*h1*h2/lambda
    d_peak = 4*h1*h2/lam;
    fprintf('2. First peak distance: d_peak_0 = 4*h1*h2/lambda = %.4f m (= %.3f km)\n', ...
            d_peak, d_peak/1000);
    fprintf('   Expected: ~125420.10 m (~125.4 km, exactly 2x last null)\n\n');

    %% 3. Power factor at last null (rho=-1)
    delta = sqrt(d_null^2 + (h1+h2)^2) - sqrt(d_null^2 + (h2-h1)^2);
    phi = 2*pi*delta/lam;
    rho = -1;
    F2 = 1 + rho^2 + 2*rho*cos(phi);
    fprintf('3. F^2 at last null (rho=-1): %.6e (expect ~0)\n\n', F2);

    %% 4. Power factor at first peak (rho=-1)
    delta = sqrt(d_peak^2 + (h1+h2)^2) - sqrt(d_peak^2 + (h2-h1)^2);
    phi = 2*pi*delta/lam;
    F2 = 1 + rho^2 + 2*rho*cos(phi);
    fprintf('4. F^2 at first peak (rho=-1): %.6f  (expect ~4)\n', F2);
    F4 = F2^2;
    fprintf('   F^4 = %.6f (expect ~16)\n\n', F4);

    %% 5. Smooth sea (rho=-0.95) at null and peak
    rho = -0.95;
    % null: F^2_min = (1+rho)^2 = 0.0025
    % peak: F^2_max = (1-rho)^2 = 3.8025
    F2_null_floor = (1+rho)^2;
    F2_peak_ceil  = (1-rho)^2;
    fprintf('5. Smooth sea (rho=-0.95):\n');
    fprintf('   F^2 floor at null = (1+rho)^2 = %.6f  (not 0)\n', F2_null_floor);
    fprintf('   F^2 ceiling at peak = (1-rho)^2 = %.6f  (not 4)\n\n', F2_peak_ceil);

    %% 6. Free space (rho=0): F^2 = 1 always
    F2_fs = 1 + 0^2 + 2*0*cos(1.0);  % phi any
    fprintf('6. Free space (rho=0): F^2 = %.6f (expect 1)\n\n', F2_fs);

    %% 7. Far-field asymptotics — F^4 at d = 200km, 500km, 1000km
    rho = -1;
    fprintf('7. Far-field F^4 (rho=-1):\n');
    for d = [200e3, 500e3, 1e6]
        delta = sqrt(d^2 + (h1+h2)^2) - sqrt(d^2 + (h2-h1)^2);
        phi = 2*pi*delta/lam;
        F2 = 1 + rho^2 + 2*rho*cos(phi);
        F4 = F2^2;
        fprintf('   d=%6.0f km: F^4 = %.6e  (expect monotonic decrease)\n', d/1000, F4);
    end

    fprintf('\n=== End ===\n');
end
