% test_rigid_body.m — Phase 2.4a cross-validation (Octave base only).
%
% Verifies attitude_from_velocity (coordinated-flight assumption,
% plan/14 § 14.3.2) against the Python implementation in
% src/workbench/physics/dynamics/rigid_body.py.
%
% Convention: yaw measured CW from North about +Up — same as the
% TRsim project heading_rad. yaw = atan2(velocity_east, velocity_north).
%
% No Toolbox calls. Pure base math.

function test_rigid_body
    % --- Pure +North velocity (heading = 0) ---
    [r, p, y] = attitude_from_velocity(0.0, 100.0, 0.0);
    expect_close('north_yaw', y, 0.0, 1e-12);
    expect_close('north_pitch', p, 0.0, 1e-12);
    expect_close('north_roll', r, 0.0, 1e-12);

    % --- Pure +East (heading = +pi/2) ---
    [~, ~, y] = attitude_from_velocity(100.0, 0.0, 0.0);
    expect_close('east_yaw', y, pi / 2, 1e-12);

    % --- 45 deg NE ---
    [~, ~, y] = attitude_from_velocity(50.0, 50.0, 0.0);
    expect_close('ne_yaw', y, pi / 4, 1e-12);

    % --- Climbing 30 deg ---
    horiz = 100.0;
    vert = horiz * tan(pi / 6);   % tan(30 deg)
    [~, p, ~] = attitude_from_velocity(0.0, horiz, vert);
    expect_close('climb_pitch', p, pi / 6, 1e-12);

    % --- Pure vertical (asin clamp) ---
    [~, p, ~] = attitude_from_velocity(0.0, 0.0, 100.0);
    expect_close('vertical_pitch', p, pi / 2, 1e-12);

    % --- Diving (negative pitch) ---
    [~, p, ~] = attitude_from_velocity(0.0, 100.0, -50.0);
    expected = asin(-50.0 / sqrt(100.0^2 + 50.0^2));
    expect_close('dive_pitch', p, expected, 1e-12);

    % --- Speed below threshold preserves attitude (test omitted —
    % requires existing-attitude argument; Python test covers it).

    printf('PASS\n');
end

function [roll, pitch, yaw] = attitude_from_velocity(vE, vN, vU)
    % Returns (roll, pitch, yaw) from velocity vector under
    % coordinated-flight assumption. Roll is always 0 at MVP Level 1.
    speed = sqrt(vE^2 + vN^2 + vU^2);
    if speed < 0.01
        roll = 0.0;
        pitch = 0.0;
        yaw = 0.0;
        return;
    end
    yaw = atan2(vE, vN);
    sin_pitch = vU / speed;
    sin_pitch = max(-1.0, min(1.0, sin_pitch));
    pitch = asin(sin_pitch);
    roll = 0.0;
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.12f, expected %.12f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.12f\n', name, actual);
    end
end
