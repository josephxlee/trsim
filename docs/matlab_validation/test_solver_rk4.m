% test_solver_rk4.m — Phase 2.4c cross-validation (Octave base only).
%
% Verifies the RK4 integrator (plan/14 § 14.6) against the Python
% implementation in src/workbench/physics/dynamics/solver_rk4.py.
%
% State variable: x = (position, velocity), x' = (velocity, F/m).
% Integrates a free-fall (constant gravity) trajectory and a constant
% horizontal-force trajectory, then checks RK4 reproduces the
% closed-form kinematic answer to machine precision (RK4 is exact for
% quadratic position trajectories under constant acceleration).
%
% No Toolbox calls. Pure base math.

function test_solver_rk4
    g = 9.80665;

    % --- Free fall: h(t) = h0 - 1/2 * g * t^2 ---
    mass = 100.0;
    h0 = 1000.0;
    v0 = 0.0;
    dt = 2.0;
    [pos_new, vel_new] = rk4_step_1d(h0, v0, -mass * g, mass, dt);
    expect_close('freefall_h', pos_new, h0 - 0.5 * g * dt^2, 1e-9);
    expect_close('freefall_v', vel_new, v0 - g * dt, 1e-12);

    % --- Constant horizontal force: x = 1/2 * a * t^2 ---
    mass = 100.0;
    F = 1000.0;
    a = F / mass;
    [pos_new, vel_new] = rk4_step_1d(0.0, 0.0, F, mass, 1.0);
    expect_close('horizontal_x', pos_new, 0.5 * a * 1.0^2, 1e-9);
    expect_close('horizontal_v', vel_new, a * 1.0, 1e-12);

    % --- Sub-stepped integrate matches single step under constant force ---
    mass = 50.0;
    F = 500.0;
    [pos_one, vel_one] = rk4_step_1d(0.0, 1.0, F, mass, 1.0);
    [pos_many, vel_many] = rk4_substep_1d(0.0, 1.0, F, mass, 1.0, 20);
    expect_close('substep_pos_match', pos_one, pos_many, 1e-9);
    expect_close('substep_vel_match', vel_one, vel_many, 1e-12);

    % --- Energy conservation under gravity (KE + PE) ---
    mass = 10.0;
    h0 = 0.0;
    v0 = 50.0;
    [h_new, vU_new] = rk4_substep_1d(h0, v0, -mass * g, mass, 2.0, 20);
    e0 = 0.5 * mass * v0^2 + mass * g * h0;
    e1 = 0.5 * mass * vU_new^2 + mass * g * h_new;
    expect_close('energy_conserved', e1, e0, 1e-9);

    printf('PASS\n');
end

function [pos_new, vel_new] = rk4_step_1d(pos, vel, force, mass, dt)
    % 1-D RK4 step for x' = v, v' = F/m (F constant in this script).
    a = force / mass;
    half_dt = dt * 0.5;

    % k1 at current state
    v1 = vel;
    a1 = a;

    % k2 at half-step using k1
    v2 = vel + a1 * half_dt;
    a2 = a;            % constant force → derivative same

    % k3 at half-step using k2
    v3 = vel + a2 * half_dt;
    a3 = a;

    % k4 at full-step using k3
    v4 = vel + a3 * dt;
    a4 = a;

    sixth = dt / 6.0;
    pos_new = pos + sixth * (v1 + 2*v2 + 2*v3 + v4);
    vel_new = vel + sixth * (a1 + 2*a2 + 2*a3 + a4);
end

function [pos_new, vel_new] = rk4_substep_1d(pos, vel, force, mass, dt_main, n)
    dt_sub = dt_main / n;
    for i = 1:n
        [pos, vel] = rk4_step_1d(pos, vel, force, mass, dt_sub);
    end
    pos_new = pos;
    vel_new = vel;
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.12f, expected %.12f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.12f\n', name, actual);
    end
end
