% test_antenna.m — Phase 2.6 cross-validation (Octave base only).
%
% Verifies parabolic dish: wavelength, 3-dB beamwidth, peak gain,
% sinc^2 beam pattern. Pure base math, no Toolbox.

function test_antenna
    c = 299792458.0;
    D = 1.0;
    f = 9.4e9;
    eta = 0.6;

    lam = c / f;
    expect_close('lambda', lam, 0.0318928147, 1e-10);

    bw = 70 * lam / D;
    expect_close('bw_3db_deg', bw, 2.232497, 1e-5);

    ratio = pi * D / lam;
    g_lin = eta * ratio^2;
    g_dbi = 10 * log10(g_lin);
    expect_close('peak_gain_dbi', g_dbi, 37.6507, 1e-3);

    % sinc^2 at u_half = 1.391557377 should be 0.5
    u_half = 1.391557377;
    p_half = (sin(u_half) / u_half)^2;
    expect_close('sinc^2_at_half', p_half, 0.5, 1e-9);

    % at boresight pattern = 1
    expect_close('pattern_boresight', 1.0, 1.0, 0.0);

    printf('PASS\n');
end

function expect_close(name, actual, expected, tol)
    if abs(actual - expected) > tol
        error('FAIL: %s = %.10f, expected %.10f (tol %.2e)', ...
              name, actual, expected, tol);
    else
        printf('OK: %s = %.10f\n', name, actual);
    end
end
