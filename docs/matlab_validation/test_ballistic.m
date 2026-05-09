% test_ballistic.m — Phase 2.4e cross-validation (Octave base only).
%
% Verifies vacuum-ballistic closed-form trajectory vs RK4 integration
% (plan/14 § 14.5.3 / § 14.6 / § 14.9.1) — same kinematics as the
% Python implementation in
% src/workbench/physics/dynamics/ballistic.py (Cd = 0).
%
% No Toolbox calls. Pure base math.

function test_ballistic
    g = 9.80665;

    % --- 45-deg projectile, v0 = 100 m/s, vacuum ---
    % Closed form:
    %   range R   = v0^2 * sin(2*theta) / g     (theta = 45 deg → R = v0^2 / g)
    %   peak h    = v0^2 * sin(theta)^2 / (2g)
    %   t_flight  = 2*v0*sin(theta) / g
    v0 = 100.0;
    theta = pi / 4;
    R_closed = v0^2 / g;
    h_peak = v0^2 * sin(theta)^2 / (2 * g);
    t_flight = 2 * v0 * sin(theta) / g;
    expect_close('R_closed', R_closed, 1019.7162, 1e-3);
    expect_close('h_peak', h_peak, 254.9290, 1e-3);
    expect_close('t_flight', t_flight, 14.4297, 1e-3);

    % --- Energy conservation: vertical launch v0 = 100 m/s ---
    % At peak (v=0): PE = m*g*h_peak should equal initial KE
    mass = 10.0;
    v0_vert = 100.0;
    h_at_peak = v0_vert^2 / (2 * g);
    KE0 = 0.5 * mass * v0_vert^2;
    PE_peak = mass * g * h_at_peak;
    expect_close('vacuum_energy_at_peak', PE_peak, KE0, 1e-9);

    % --- RK4 integration of free-fall reproduces closed form to
    %     machine precision (constant gravity → quadratic position) ---
    [pos_new, vel_new] = rk4_step_1d(0.0, v0_vert, -mass * g, mass, 5.0);
    expect_close('rk4_h_5s', pos_new, v0_vert * 5.0 - 0.5 * g * 25.0, 1e-9);
    expect_close('rk4_v_5s', vel_new, v0_vert - g * 5.0, 1e-12);

    printf('PASS\n');
end

function [pos_new, vel_new] = rk4_step_1d(pos, vel, force, mass, dt)
    a = force / mass;
    half_dt = dt * 0.5;
    v1 = vel;          a1 = a;
    v2 = vel + a1 * half_dt;  a2 = a;
    v3 = vel + a2 * half_dt;  a3 = a;
    v4 = vel + a3 * dt;       a4 = a;
    sixth = dt / 6.0;
    pos_new = pos + sixth * (v1 + 2*v2 + 2*v3 + v4);
    vel_new = vel + sixth * (a1 + 2*a2 + 2*a3 + a4);
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.9f, expected %.9f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.9f\n', name, actual);
    end
end
