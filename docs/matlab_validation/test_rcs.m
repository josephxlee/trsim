function test_rcs()
%% test_rcs.m - TRsim physics/reflection/rcs_single.py reference values
%
% Plain MATLAB / GNU Octave (no Toolbox).
%
% Usage:
%   octave docs/matlab_validation/test_rcs.m
%
% Author: TRsim Phase 1.5 cross-validation.

    fprintf('=== TRsim physics/reflection/rcs_single.py reference values ===\n\n');

    C = 299792458;
    fc = 9.4e9;             % X-band
    lam = C / fc;           % ~= 0.03189 m
    fprintf('X-band: f_c=%.1fGHz, lambda=%.6f m\n\n', fc/1e9, lam);

    %% 1. Sphere geometric (a=1m)
    s = pi * 1.0^2;
    fprintf('1. Sphere a=1m geometric:    sigma = %.6f m^2  (= %.4f dBsm)\n', s, 10*log10(s));
    fprintf('   Expected: pi ~= 3.141593, dBsm ~= 4.9715\n\n');

    %% 2. Sphere geometric (a=0.5m)
    s = pi * 0.5^2;
    fprintf('2. Sphere a=0.5m geometric:  sigma = %.6f m^2\n', s);
    fprintf('   Expected: pi/4 ~= 0.785398\n\n');

    %% 3. Sphere Rayleigh (a=1mm, lam=1m)
    s = (4*pi^5/3) * (1e-3)^6 / 1.0^4;
    fprintf('3. Sphere a=1mm, lam=1m (Rayleigh): sigma = %.6e m^2\n', s);
    fprintf('   Expected: ~4.0772e-16\n\n');

    %% 4. Flat plate (A=1m^2, X-band)
    s = 4*pi * 1.0^2 / lam^2;
    fprintf('4. Plate A=1m^2 X-band:      sigma = %.4f m^2  (= %.4f dBsm)\n', s, 10*log10(s));
    fprintf('   Expected: ~12354.4713 m^2 (~40.92 dBsm)\n\n');

    %% 5. Cylinder broadside (a=0.1m, L=1m, X-band)
    s = 2*pi * 0.1 * 1.0^2 / lam;
    fprintf('5. Cylinder a=0.1m L=1m X:   sigma = %.4f m^2  (= %.4f dBsm)\n', s, 10*log10(s));
    fprintf('   Expected: ~19.7009 m^2 (~12.94 dBsm)\n\n');

    %% 6. Trihedral (L=0.5m, X-band)
    s = 12*pi * 0.5^4 / lam^2;
    fprintf('6. Trihedral L=0.5m X-band:  sigma = %.4f m^2  (= %.4f dBsm)\n', s, 10*log10(s));
    fprintf('   Expected: ~2316.4634 m^2 (~33.65 dBsm)\n\n');

    %% 7. Dihedral (w=1m, h=0.5m, X-band)
    s = 8*pi * (1.0*0.5)^2 / lam^2;
    fprintf('7. Dihedral 1m x 0.5m X:     sigma = %.4f m^2  (= %.4f dBsm)\n', s, 10*log10(s));
    fprintf('   Expected: ~6177.2357 m^2 (~37.91 dBsm)\n\n');

    %% 8. dBsm round-trips
    fprintf('8. dBsm round-trips:\n');
    for x = [1e-6, 1e-3, 1.0, 100.0, 1e6]
        db = 10*log10(x);
        back = 10^(db/10);
        fprintf('   sigma=%.6e -> %.4f dBsm -> %.6e (rel err=%.2e)\n', ...
                x, db, back, abs(back-x)/x);
    end

    fprintf('\n=== End ===\n');
end
