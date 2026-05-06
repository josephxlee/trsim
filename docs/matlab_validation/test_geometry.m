%% test_geometry.m — TRsim physics/geometry.py reference values
%
% Goal: produce reference numbers for cross-validation of TRsim's
%       physics.geometry primitives. Uses ONLY base MATLAB / Octave
%       (no Mapping Toolbox required) — implements WGS84 / ECEF / ENU /
%       AER conversions via the standard NIMA TR8350.2 formulas.
%
% Compatibility: MATLAB R2014+ or GNU Octave 5+ (any).
%
% Usage:
%   1. Open this file in MATLAB or Octave.
%   2. Run the whole script. All 9 reference cases print to console.
%   3. Compare values against TRsim test expectations
%      (tests/physics/test_geometry.py).
%   4. Report any discrepancy > 1 mm to update the goldens.
%
% Reference: NIMA TR8350.2 (WGS84). Bowring (1976) closed-form ECEF inverse.
% Convention: ENU = right-handed East/North/Up; AZ = clockwise from North.
%
% Author: TRsim Phase 1.1 cross-validation.

clear; clc;
fprintf('=== TRsim physics/geometry.py reference values ===\n');
fprintf('(plain MATLAB / Octave, no Toolbox)\n\n');

%% WGS84 constants
A  = 6378137.0;                % semi-major [m]
F  = 1/298.257223563;          % flattening
B  = A*(1-F);                  % semi-minor [m]
E2 = F*(2-F);                  % e^2
EP2 = E2/(1-E2);               % e'^2 (second eccentricity squared)
R_MEAN = 6371008.7714;         % mean Earth radius [m]

fprintf('WGS84 a  = %.4f\n', A);
fprintf('WGS84 b  = %.4f\n', B);
fprintf('WGS84 e2 = %.14f\n\n', E2);

%% 1. WGS84 → ECEF — equator / prime meridian
[x, y, z] = wgs84_to_ecef(0, 0, 0, A, E2);
fprintf('1. (lat=0, lon=0, alt=0) → ECEF = (%.6f, %.6f, %.6f) m\n', x, y, z);
fprintf('   Expected ≈ (6378137.0, 0.0, 0.0)   [a, 0, 0]\n\n');

%% 2. WGS84 → ECEF — north pole
[x, y, z] = wgs84_to_ecef(90, 0, 0, A, E2);
fprintf('2. (lat=90, lon=0, alt=0) → ECEF = (%.6f, %.6f, %.6f) m\n', x, y, z);
fprintf('   Expected ≈ (0.0, 0.0, 6356752.3142)   [0, 0, b]\n\n');

%% 3. WGS84 → ECEF — Seoul (37.5665°N, 126.9780°E, 0m)
[x, y, z] = wgs84_to_ecef(37.5665, 126.9780, 0, A, E2);
fprintf('3. Seoul (37.5665, 126.9780, 0) → ECEF = (%.6f, %.6f, %.6f) m\n', x, y, z);
fprintf('   TRsim test asserts ~(-3043032.5, 4036887.6, 3863026.4) ± 10 m\n');
fprintf('   ↳ MATLAB precise values feed back into pytest goldens.\n\n');

%% 4. WGS84 → ECEF round-trip — Sydney
[x, y, z] = wgs84_to_ecef(-33.8688, 151.2093, 100, A, E2);
[lat2, lon2, alt2] = ecef_to_wgs84(x, y, z, A, B, E2, EP2);
fprintf('4. Sydney round-trip\n');
fprintf('   in : (-33.8688, 151.2093, 100.0)\n');
fprintf('   ECEF: (%.4f, %.4f, %.4f)\n', x, y, z);
fprintf('   out: (%.10f, %.10f, %.6f)\n', lat2, lon2, alt2);
fprintf('   diff: (%.3e, %.3e, %.3e)\n\n', lat2 + 33.8688, lon2 - 151.2093, alt2 - 100);

%% 5. ECEF → ENU at origin
origin = [37.5665, 126.9780, 50.0];
[ox, oy, oz] = wgs84_to_ecef(origin(1), origin(2), origin(3), A, E2);
[e, n, u] = ecef_to_enu(ox, oy, oz, origin(1), origin(2), origin(3), A, E2);
fprintf('5. ENU at origin = (%.6e, %.6e, %.6e) m\n', e, n, u);
fprintf('   Expected ≈ (0, 0, 0)\n\n');

%% 6. ENU round-trip — 100 m east, 200 m north, 50 m up
e_in = 100.0; n_in = 200.0; u_in = 50.0;
[xx, yy, zz] = enu_to_ecef(e_in, n_in, u_in, origin(1), origin(2), origin(3), A, E2);
[e_out, n_out, u_out] = ecef_to_enu(xx, yy, zz, origin(1), origin(2), origin(3), A, E2);
fprintf('6. ENU round-trip (100, 200, 50)\n');
fprintf('   ECEF: (%.4f, %.4f, %.4f)\n', xx, yy, zz);
fprintf('   ENU back: (%.10f, %.10f, %.10f)\n\n', e_out, n_out, u_out);

%% 7. AER ↔ ENU — cardinal directions (radar convention: AZ from North CW)
% North: az=0°, el=0°, r=100
[e, n, u] = aer_to_enu(0, 0, 100);
fprintf('7a. AER (0°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, 100, 0)\n');
% East
[e, n, u] = aer_to_enu(90, 0, 100);
fprintf('7b. AER (90°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (100, 0, 0)\n');
% South
[e, n, u] = aer_to_enu(180, 0, 100);
fprintf('7c. AER (180°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, -100, 0)\n');
% Zenith
[e, n, u] = aer_to_enu(0, 90, 100);
fprintf('7d. AER (0°, 90°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, 0, 100)\n\n');

%% 8. AER round-trip — (45°, 30°, 1000 m)
[e, n, u] = aer_to_enu(45, 30, 1000);
[az, el, slant] = enu_to_aer(e, n, u);
fprintf('8. AER round-trip (45°, 30°, 1000)\n');
fprintf('   ENU: (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('   back: (%.10f°, %.10f°, %.6f m)\n\n', az, el, slant);

%% 9. Haversine — 1° at equator, quarter-circle
d_1deg = haversine_m(0, 0, 0, 1, R_MEAN);
d_quart = haversine_m(0, 0, 90, 0, R_MEAN);
fprintf('9. Haversine (mean R = %.4f m)\n', R_MEAN);
fprintf('   (0,0)→(0,1°)  = %.4f m   Expected = %.4f m  (deg2rad(1)*R)\n', ...
        d_1deg, deg2rad(1)*R_MEAN);
fprintf('   (0,0)→(90,0°) = %.4f m   Expected = %.4f m  (pi/2*R)\n\n', ...
        d_quart, pi/2*R_MEAN);

fprintf('=== End. Compare to tests/physics/test_geometry.py ===\n');


% ========================================================================
% Helper functions (manual WGS84 / ENU / AER — no Toolbox)
% ========================================================================

function [x, y, z] = wgs84_to_ecef(lat_deg, lon_deg, alt_m, A, E2)
    lat = deg2rad(lat_deg);
    lon = deg2rad(lon_deg);
    sl = sin(lat); cl = cos(lat);
    so = sin(lon); co = cos(lon);
    N = A / sqrt(1 - E2*sl*sl);
    x = (N + alt_m) * cl * co;
    y = (N + alt_m) * cl * so;
    z = (N*(1-E2) + alt_m) * sl;
end

function [lat_deg, lon_deg, alt_m] = ecef_to_wgs84(x, y, z, A, B, E2, EP2)
    p = sqrt(x*x + y*y);
    lon = atan2(y, x);
    theta = atan2(z*A, p*B);
    st = sin(theta); ct = cos(theta);
    lat = atan2(z + EP2*B*st^3, p - E2*A*ct^3);
    sl = sin(lat);
    N = A / sqrt(1 - E2*sl*sl);
    alt_m = p/cos(lat) - N;
    lat_deg = rad2deg(lat);
    lon_deg = rad2deg(lon);
end

function [e, n, u] = ecef_to_enu(x, y, z, olat_deg, olon_deg, oalt_m, A, E2)
    [ox, oy, oz] = wgs84_to_ecef(olat_deg, olon_deg, oalt_m, A, E2);
    dx = x - ox; dy = y - oy; dz = z - oz;
    olat = deg2rad(olat_deg); olon = deg2rad(olon_deg);
    sL = sin(olat); cL = cos(olat); sO = sin(olon); cO = cos(olon);
    e = -sO*dx + cO*dy;
    n = -sL*cO*dx - sL*sO*dy + cL*dz;
    u =  cL*cO*dx + cL*sO*dy + sL*dz;
end

function [x, y, z] = enu_to_ecef(e, n, u, olat_deg, olon_deg, oalt_m, A, E2)
    [ox, oy, oz] = wgs84_to_ecef(olat_deg, olon_deg, oalt_m, A, E2);
    olat = deg2rad(olat_deg); olon = deg2rad(olon_deg);
    sL = sin(olat); cL = cos(olat); sO = sin(olon); cO = cos(olon);
    dx = -sO*e - sL*cO*n + cL*cO*u;
    dy =  cO*e - sL*sO*n + cL*sO*u;
    dz =        cL*n     + sL*u;
    x = ox + dx; y = oy + dy; z = oz + dz;
end

function [e, n, u] = aer_to_enu(az_deg, el_deg, r)
    % Radar convention: AZ = clockwise from North; EL = above horizon.
    az = deg2rad(az_deg); el = deg2rad(el_deg);
    e = r * cos(el) * sin(az);
    n = r * cos(el) * cos(az);
    u = r * sin(el);
end

function [az_deg, el_deg, range_m] = enu_to_aer(e, n, u)
    horiz = hypot(e, n);
    range_m = hypot(horiz, u);
    az = atan2(e, n);
    if az < 0
        az = az + 2*pi;
    end
    el = atan2(u, horiz);
    az_deg = rad2deg(az);
    el_deg = rad2deg(el);
end

function d = haversine_m(lat1_deg, lon1_deg, lat2_deg, lon2_deg, R)
    L1 = deg2rad(lat1_deg); L2 = deg2rad(lat2_deg);
    dL = deg2rad(lat2_deg - lat1_deg);
    dO = deg2rad(lon2_deg - lon1_deg);
    a = sin(dL/2)^2 + cos(L1)*cos(L2)*sin(dO/2)^2;
    c = 2 * asin(sqrt(a));
    d = R * c;
end


%% Octave / older MATLAB compatibility — define deg2rad/rad2deg if missing
% Modern MATLAB (R2015b+) and Octave 4+ have these built in. The blocks
% below are no-ops on those; the script also runs on stripped-down Octave.
%
% (Inline fallback: rely on built-in. If your runtime errors on deg2rad,
%  uncomment these lines and move them above the helper functions.)
%
% function r = deg2rad(d); r = d * pi / 180; end
% function d = rad2deg(r); d = r * 180 / pi; end
