function output = vault_engine_check()
% Execute both toolbox operations to check actual availability, not license names.
x = (1:9)';
filtered = sgolayfilt(x,2,7);
[d,aligned] = procrustes([x,x.^2],[x,x.^2],'Scaling',false,'Reflection',false);
assert(all(isfinite(filtered)) && all(isfinite(aligned(:))) && d < 1e-9, ...
    'vault:Setup','MATLAB toolbox preflight failed');
output = jsonencode(struct('release',version('-release'),'license_source','current-user'));
end
