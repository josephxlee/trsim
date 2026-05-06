%% test_geometry.m — TRsim physics/geometry.py reference values
%
% Goal: produce reference numbers for cross-validation of TRsim's
%       physics.geometry primitives against MATLAB's standard
%       Mapping Toolbox (geodetic2ecef / ecef2enu / aer2enu, etc.).
%
% Usage:
%   1. Open MATLAB on a machine with Mapping Toolbox.
%   2. Run this script.
%   3. Compare printed values against TRsim test expectations
%      (tests/physics/test_geometry.py).
%   4. Report any discrepancy > tolerance to update the golden tests.
%
% Tolerances:
%   - WGS84 ↔ ECEF : sub-mm on input precision
%   - ENU / AER    : sub-mm on input precision
%
% Author: TRsim Phase 1 cross-validation.
% Refs  : NIMA TR8350.2, MATLAB Mapping Toolbox docs.

clear; clc;
fprintf('=== TRsim physics/geometry.py reference values ===\n\n');

E = referenceEllipsoid('wgs84');

%% 1. WGS84 → ECEF — equator / prime meridian
[x, y, z] = geodetic2ecef(E, 0, 0, 0);
fprintf('1. (lat=0, lon=0, alt=0) → ECEF = (%.6f, %.6f, %.6f) m\n', x, y, z);
fprintf('   Expected ≈ (6378137.0, 0.0, 0.0)   [a, 0, 0]\n\n');

%% 2. WGS84 → ECEF — north pole
[x, y, z] = geodetic2ecef(E, 90, 0, 0);
fprintf('2. (lat=90, lon=0, alt=0) → ECEF = (%.6f, %.6f, %.6f) m\n', x, y, z);
fprintf('   Expected ≈ (0.0, 0.0, 6356752.3142)  [0, 0, b]\n\n');

%% 3. WGS84 → ECEF — Seoul landmark (37.5665°N, 126.9780°E, 0m)
[x, y, z] = geodetic2ecef(E, 37.5665, 126.9780, 0);
fprintf('3. Seoul (37.5665, 126.9780, 0) → ECEF = (%.6f, %.6f, %.6f) m\n', ...
    x, y, z);
fprintf('   TRsim test asserts ~(-3043032.5, 4036887.6, 3863026.4) ± 10 m\n\n');

%% 4. WGS84 → ECEF round-trip — Sydney
[x, y, z] = geodetic2ecef(E, -33.8688, 151.2093, 100);
[lat2, lon2, alt2] = ecef2geodetic(E, x, y, z);
fprintf('4. Sydney round-trip\n');
fprintf('   in : (-33.8688, 151.2093, 100.0)\n');
fprintf('   ECEF: (%.4f, %.4f, %.4f)\n', x, y, z);
fprintf('   out: (%.10f, %.10f, %.6f)\n', lat2, lon2, alt2);
fprintf('   diff: (%.3e, %.3e, %.3e)\n\n', lat2 + 33.8688, lon2 - 151.2093, alt2 - 100);

%% 5. ECEF → ENU — at origin
origin_lat = 37.5665; origin_lon = 126.9780; origin_alt = 50.0;
[ox, oy, oz] = geodetic2ecef(E, origin_lat, origin_lon, origin_alt);
[e, n, u] = ecef2enu(ox, oy, oz, origin_lat, origin_lon, origin_alt, E);
fprintf('5. ENU at origin = (%.6e, %.6e, %.6e) m\n', e, n, u);
fprintf('   Expected ≈ (0, 0, 0)\n\n');

%% 6. ENU round-trip — 100 m east, 200 m north, 50 m up
e_in = 100.0; n_in = 200.0; u_in = 50.0;
[x2, y2, z2] = enu2ecef(e_in, n_in, u_in, origin_lat, origin_lon, origin_alt, E);
[e_out, n_out, u_out] = ecef2enu(x2, y2, z2, origin_lat, origin_lon, origin_alt, E);
fprintf('6. ENU round-trip (100, 200, 50)\n');
fprintf('   ECEF: (%.4f, %.4f, %.4f)\n', x2, y2, z2);
fprintf('   ENU back: (%.10f, %.10f, %.10f)\n\n', e_out, n_out, u_out);

%% 7. AER ↔ ENU — cardinal directions
% MATLAB's aer2enu uses the SAME convention TRsim uses
%   (azimuth: clockwise from North, elevation: above horizon)

% North: az=0°, el=0°, r=100
[e, n, u] = aer2enu(0, 0, 100);
fprintf('7a. AER (0°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, 100, 0)\n');

% East: az=90°, el=0°, r=100
[e, n, u] = aer2enu(90, 0, 100);
fprintf('7b. AER (90°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (100, 0, 0)\n');

% South: az=180°, el=0°, r=100
[e, n, u] = aer2enu(180, 0, 100);
fprintf('7c. AER (180°, 0°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, -100, 0)\n');

% Zenith: az=0°, el=90°, r=100
[e, n, u] = aer2enu(0, 90, 100);
fprintf('7d. AER (0°, 90°, 100) → ENU = (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('    Expected ≈ (0, 0, 100)\n\n');

%% 8. AER round-trip — (45°, 30°, 1000 m)
[e, n, u] = aer2enu(45, 30, 1000);
[az, el, slant] = enu2aer(e, n, u);
fprintf('8. AER round-trip (45°, 30°, 1000)\n');
fprintf('   ENU: (%.6f, %.6f, %.6f)\n', e, n, u);
fprintf('   back: (%.10f°, %.10f°, %.6f)\n\n', az, el, slant);

%% 9. Haversine — 1° at equator
% MATLAB's distance() with great circle — note this uses degrees and returns
% the distance ALONG the great-circle arc on a SPHERE of radius R.
R_mean = 6371008.7714;
[arc_deg] = distance('gc', 0, 0, 0, 1);   % returns angular distance
d_m = arc_deg * pi / 180 * R_mean;
fprintf('9. Haversine (0,0)→(0,1°) ≈ %.4f m\n', d_m);
fprintf('   Expected ≈ %.4f m  (1° = π/180 × R_mean)\n\n', deg2rad(1) * R_mean);

%% Summary
fprintf('=== End. Compare values to tests/physics/test_geometry.py ===\n');
