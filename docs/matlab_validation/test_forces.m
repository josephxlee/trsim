% test_forces.m — Phase 2.4b cross-validation (Octave base only).
%
% Verifies external force model (gravity / drag / lift / thrust curve)
% against the Python implementation in
% src/workbench/physics/dynamics/forces.py.
%
% No Toolbox calls. Pure base math.

function test_forces
    g = 9.80665;
    rho_sea = 1.225;

    % --- Gravity: 1000 kg target ---
    Fg_z = -1000 * g;
    expect_close('gravity_z', Fg_z, -9806.65, 1e-6);

    % --- Drag at sea level: v=100 East, Cd=0.5, A=2 ---
    v = 100.0;
    Cd = 0.5;
    A = 2.0;
    Fd_mag = 0.5 * rho_sea * v^2 * Cd * A;
    expect_close('drag_sea_v100', Fd_mag, 6125.0, 1e-3);

    % --- ISA density at 1000 m, then drag magnitude ---
    L = 0.0065;
    R = 287.058;
    P0 = 101325.0;
    T0 = 288.15;
    expo = g / (R * L);
    T1 = T0 - L * 1000;
    P1 = P0 * (T1 / T0)^expo;
    rho1 = P1 / (R * T1);
    Fd_1km = 0.5 * rho1 * v^2 * Cd * A;
    expect_close('drag_1km_rho', rho1, 1.111625, 1e-5);
    expect_close('drag_1km_v100', Fd_1km, 0.5 * rho1 * 100^2 * Cd * A, 1e-9);

    % --- Lift trim at reference (h = h_ref, v_up = 0) ---
    mass = 1000.0;
    F_lift_trim = mass * g;
    expect_close('lift_trim', F_lift_trim, 9806.65, 1e-6);

    % --- Lift below reference: kp*delta_h ---
    kp = 10.0;
    delta_h = 100.0;     % h_ref - h
    F_lift = mass * g + kp * delta_h;
    expect_close('lift_below_ref', F_lift, mass * g + 1000.0, 1e-9);

    % --- Lift damping: kd * v_up ---
    kd = 20.0;
    v_up = 5.0;
    F_lift_damped = mass * g - kd * v_up;
    expect_close('lift_damped', F_lift_damped, mass * g - 100.0, 1e-9);

    % --- Thrust curve: linear interp between (0,0) and (1,1000) ---
    % at t = 0.5 → 500 N
    F_thrust = thrust_curve_linear(0.5, [0.0 0.0; 1.0 1000.0; 2.0 0.0]);
    expect_close('thrust_t0p5', F_thrust, 500.0, 1e-9);
    F_thrust = thrust_curve_linear(1.5, [0.0 0.0; 1.0 1000.0; 2.0 0.0]);
    expect_close('thrust_t1p5', F_thrust, 500.0, 1e-9);

    % --- Thrust outside range: clamps to last ---
    F_thrust = thrust_curve_linear(10.0, [0.0 100.0; 5.0 200.0]);
    expect_close('thrust_clamp_high', F_thrust, 200.0, 1e-9);
    F_thrust = thrust_curve_linear(-1.0, [0.0 100.0; 5.0 200.0]);
    expect_close('thrust_clamp_low', F_thrust, 100.0, 1e-9);

    printf('PASS\n');
end

function n = thrust_curve_linear(t_query, samples)
    % samples: Nx2 [t_s, thrust_N]; assumed sorted strictly increasing in t.
    N = size(samples, 1);
    if t_query <= samples(1, 1)
        n = samples(1, 2);
        return;
    end
    if t_query >= samples(N, 1)
        n = samples(N, 2);
        return;
    end
    for i = 1:(N - 1)
        t0 = samples(i, 1);
        t1 = samples(i + 1, 1);
        if t0 <= t_query && t_query <= t1
            n0 = samples(i, 2);
            n1 = samples(i + 1, 2);
            w = (t_query - t0) / (t1 - t0);
            n = n0 + w * (n1 - n0);
            return;
        end
    end
    n = samples(N, 2);
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.9f, expected %.9f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.9f\n', name, actual);
    end
end
