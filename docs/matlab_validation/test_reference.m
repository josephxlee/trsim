% test_reference.m — Phase 2.4d cross-validation (Octave base only).
%
% Verifies trajectory linear-interpolation (plan/14 § 14.7) against
% the Python implementation in
% src/workbench/physics/dynamics/reference.py.
%
% No Toolbox calls. Pure base math.

function test_reference
    % --- Two-waypoint trajectory: midpoint ---
    % t_s=0 → (0, 0, 1000), t_s=10 → (100, 200, 1500)
    [e, n, alt] = interp_ref(5.0, [0 0 0 1000; 10 100 200 1500]);
    expect_close('mid_east', e, 50.0, 1e-12);
    expect_close('mid_north', n, 100.0, 1e-12);
    expect_close('mid_alt', alt, 1250.0, 1e-12);

    % --- Quarter point ---
    [e, n, alt] = interp_ref(1.0, [0 0 0 0; 4 400 800 2000]);
    expect_close('q_east', e, 100.0, 1e-12);
    expect_close('q_north', n, 200.0, 1e-12);
    expect_close('q_alt', alt, 500.0, 1e-12);

    % --- Clamp below first ---
    [e, n, alt] = interp_ref(-5.0, [0 0 0 1000; 10 100 0 1000]);
    expect_close('clamp_below_east', e, 0.0, 1e-12);

    % --- Clamp above last ---
    [e, n, alt] = interp_ref(15.0, [0 0 0 1000; 10 100 0 1000]);
    expect_close('clamp_above_east', e, 100.0, 1e-12);

    % --- Multi-segment: pick correct segment ---
    % Segments: [0..10] east 0→100, [10..20] east 100→100 (constant), north 0→200
    [e, n, alt] = interp_ref(15.0, [0 0 0 0; 10 100 0 0; 20 100 200 0]);
    expect_close('multi_east', e, 100.0, 1e-12);
    expect_close('multi_north', n, 100.0, 1e-12);

    printf('PASS\n');
end

function [east, north, alt] = interp_ref(t_query, samples)
    % samples: Nx4 [t_s east_m north_m alt_m]; strictly increasing in t.
    N = size(samples, 1);
    if N == 0
        error('empty trajectory');
    end
    if N == 1 || t_query <= samples(1, 1)
        east = samples(1, 2);
        north = samples(1, 3);
        alt = samples(1, 4);
        return;
    end
    if t_query >= samples(N, 1)
        east = samples(N, 2);
        north = samples(N, 3);
        alt = samples(N, 4);
        return;
    end
    for i = 1:(N - 1)
        t0 = samples(i, 1);
        t1 = samples(i + 1, 1);
        if t0 <= t_query && t_query <= t1
            w = (t_query - t0) / (t1 - t0);
            east = samples(i, 2) + w * (samples(i + 1, 2) - samples(i, 2));
            north = samples(i, 3) + w * (samples(i + 1, 3) - samples(i, 3));
            alt = samples(i, 4) + w * (samples(i + 1, 4) - samples(i, 4));
            return;
        end
    end
    east = samples(N, 2);
    north = samples(N, 3);
    alt = samples(N, 4);
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.12f, expected %.12f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.12f\n', name, actual);
    end
end
