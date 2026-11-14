% Run in desktop MATLAB or MATLAB Online, including the Basic version.
% No Compiler SDK is required to exercise the algorithms directly.
root = fileparts(mfilename('fullpath'));
addpath(fullfile(root, 'src'));
results = runtests(fullfile(root, 'tests'));
disp(table(results));
assertSuccess(results);
fprintf('THE VAULT MATLAB algorithm tests passed.\n');
fprintf('This verifies MATLAB source execution; it does not compile the Runtime package.\n');
