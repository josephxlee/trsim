% test_surface_vessel.m — Phase 2.4f cross-validation (Octave base only).
%
% Verifies wave heave / roll / pitch oscillation + heave-velocity
% derivative (plan/14 § 14.5.4) against the Python implementation in
% src/workbench/physics/dynamics/surface_vessel.py.
%
% No Toolbox calls. Pure base math.

function test_surface_vessel
    % --- Wave coupling: large_ship parameters ---
    heave_factor = 0.3;
    pitch_factor = 0.05;
    roll_factor = 0.08;
    A = 2.0;          % wave amplitude [m]
    T = 12.0;         % wave period [s] (large_ship natural)
    omega = 2 * pi / T;

    % --- At t = 0: sin(0) = 0 → all oscillations zero ---
    [h, r, p] = wave_oscillation(heave_factor, pitch_factor, roll_factor, A, T, 0.0);
    expect_close('t0_heave', h, 0.0, 1e-12);
    expect_close('t0_roll', r, 0.0, 1e-12);
    expect_close('t0_pitch', p, 0.0, 1e-12);

    % --- At t = T/4: sin(pi/2) = 1 → peak ---
    [h, r, p] = wave_oscillation(heave_factor, pitch_factor, roll_factor, A, T, T / 4);
    expect_close('peak_heave', h, A * heave_factor, 1e-12);
    expect_close('peak_roll', r, A * roll_factor, 1e-12);
    expect_close('peak_pitch', p, A * pitch_factor, 1e-12);

    % --- Heave velocity at t = 0: cos(0) = 1 → omega * A * heave_factor ---
    v = wave_heave_velocity(heave_factor, A, T, 0.0);
    expect_close('v_heave_t0', v, omega * A * heave_factor, 1e-12);

    % --- Heave velocity at t = T/4: cos(pi/2) = 0 ---
    v = wave_heave_velocity(heave_factor, A, T, T / 4);
    expect_close('v_heave_peak', v, 0.0, 1e-12);

    % --- Zero amplitude → all zeros ---
    [h, r, p] = wave_oscillation(heave_factor, pitch_factor, roll_factor, 0.0, T, 5.0);
    expect_close('zero_amp_heave', h, 0.0, 1e-12);
    expect_close('zero_amp_roll', r, 0.0, 1e-12);
    expect_close('zero_amp_pitch', p, 0.0, 1e-12);

    printf('PASS\n');
end

function [heave, roll, pitch] = wave_oscillation(hf, pf, rf, amp, period, t)
    if period <= 0 || amp == 0
        heave = 0; roll = 0; pitch = 0;
        return;
    end
    omega = 2 * pi / period;
    base = amp * sin(omega * t);
    heave = hf * base;
    roll = rf * base;
    pitch = pf * base;
end

function v = wave_heave_velocity(hf, amp, period, t)
    if period <= 0 || amp == 0
        v = 0;
        return;
    end
    omega = 2 * pi / period;
    v = hf * amp * omega * cos(omega * t);
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.12f, expected %.12f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.12f\n', name, actual);
    end
end
