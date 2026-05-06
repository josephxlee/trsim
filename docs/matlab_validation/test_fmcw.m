function test_fmcw()
%% test_fmcw.m — TRsim physics/propagation/fmcw.py reference values
%
% Plain MATLAB / GNU Octave (no Toolbox).
%
% Usage:
%   octave docs/matlab_validation/test_fmcw.m
%   matlab -batch "run('docs/matlab_validation/test_fmcw.m')"
%
% Author: TRsim Phase 1.3 cross-validation.

    fprintf('=== TRsim physics/propagation/fmcw.py reference values ===\n');
    fprintf('(plain MATLAB / Octave)\n\n');

    C = 299792458.0;            % speed of light [m/s] (SI exact)

    %% 1. Beat freq — R=1 km, B=100 MHz, T=1 ms
    R = 1000;  B = 100e6;  T = 1e-3;
    f_beat = beat_freq(R, B, T, C);
    fprintf('1. Beat freq (R=%.1f m, B=%.0f MHz, T=%.1f ms)\n', R, B/1e6, T*1e3);
    fprintf('   f_beat = %.6f Hz\n', f_beat);
    fprintf('   Expected ≈ 667128.184500 Hz\n\n');

    %% 2. Beat freq linear in R
    b1 = beat_freq(1000, B, T, C);
    b2 = beat_freq(2000, B, T, C);
    fprintf('2. Beat scaling: b(2km)/b(1km) = %.10f  (expected 2.0)\n\n', b2/b1);

    %% 3. Doppler — v=10 m/s @ 9.4 GHz X-band
    v = 10;  fc = 9.4e9;
    f_d = doppler(v, fc, C);
    fprintf('3. Doppler (v=%.1f m/s, fc=%.1f GHz)\n', v, fc/1e9);
    fprintf('   f_D = %.6f Hz\n', f_d);
    fprintf('   Expected ≈ 627.121829 Hz\n\n');

    %% 4. Doppler sign — receding
    f_d_neg = doppler(-50, fc, C);
    fprintf('4. Doppler sign (v=-50 m/s receding) = %.4f Hz  (expect < 0)\n\n', f_d_neg);

    %% 5. Triangle beats — stationary at 1km
    [f_up, f_down] = triangle_beats(1000, 0, B, T, fc, C);
    fprintf('5. Stationary 1km: f_up=%.6f, f_down=%.6f  (equal expected)\n\n', f_up, f_down);

    %% 6. Triangle beats — approaching 20 m/s at 1km
    [f_up, f_down] = triangle_beats(1000, 20, B, T, fc, C);
    fprintf('6. Approaching 20m/s @ 1km:\n');
    fprintf('   f_up   = %.6f Hz   (range - doppler)\n', f_up);
    fprintf('   f_down = %.6f Hz   (range + doppler)\n', f_down);
    fprintf('   diff   = %.6f Hz   (= 2·f_D ≈ 2509.49)\n\n', f_down - f_up);

    %% 7. Round-trip — (R=5km, v=100 m/s) → beats → (R, v)
    R0 = 5000;  v0 = 100;
    [fu, fd] = triangle_beats(R0, v0, B, T, fc, C);
    [R_back, v_back] = pair_to_range_vel(fu, fd, B, T, fc, C);
    fprintf('7. Round-trip (R=%.1f, v=%.1f)\n', R0, v0);
    fprintf('   beats = (%.4f, %.4f) Hz\n', fu, fd);
    fprintf('   back  = (%.10f, %.10f)\n', R_back, v_back);
    fprintf('   diff  = (%.3e, %.3e)\n\n', R_back - R0, v_back - v0);

    %% 8. Resolutions
    dR  = C / (2*B);
    dfD = 1.0 / 1e-2;
    dV  = C / (2*fc*1e-2);
    lam = C / fc;
    fprintf('8. Resolutions @ B=100MHz, T_obs=10ms, fc=9.4GHz\n');
    fprintf('   ΔR  = %.6f m       Expected ≈ 1.498962 m\n', dR);
    fprintf('   Δf_D = %.6f Hz     Expected = 100.0 Hz\n', dfD);
    fprintf('   Δv  = %.6f m/s     Expected ≈ 1.594641 m/s\n', dV);
    fprintf('   λ   = %.6f m       Expected ≈ 0.031893 m  (X-band)\n\n', lam);

    fprintf('=== End ===\n');
end


function f = beat_freq(R, B, T, C)
    f = 2 * R * B / (C * T);
end

function f = doppler(v, fc, C)
    f = 2 * v * fc / C;
end

function [f_up, f_down] = triangle_beats(R, v, B, T, fc, C)
    f_R = beat_freq(R, B, T, C);
    f_D = doppler(v, fc, C);
    f_up   = f_R - f_D;
    f_down = f_R + f_D;
end

function [R, v] = pair_to_range_vel(f_up, f_down, B, T, fc, C)
    f_R = (f_up + f_down) / 2;
    f_D = (f_down - f_up) / 2;
    R = f_R * C * T / (2 * B);
    v = f_D * C / (2 * fc);
end
