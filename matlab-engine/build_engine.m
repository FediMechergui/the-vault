% Run from /workspace in the Linux compiler container. Runtime artifacts are platform-specific.
root = fileparts(mfilename('fullpath'));
addpath(fullfile(root,'src'));
% The compiler performs the authoritative Compiler / SDK license checkout.
% Let it report entitlement failures rather than guessing FlexNet feature names.
results = compiler.build.pythonPackage(fullfile(root,'src','vaulte_engine.m'), ...
    'PackageName','vault_matlab','OutputDir',fullfile(root,'build','vault_matlab'), ...
    'AdditionalFiles',fullfile(root,'src'));
disp(results);
fprintf('Build complete. Build the Runtime service with compose.matlab.yml.\n');
