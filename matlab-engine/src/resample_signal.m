function y = resample_signal(x, count, times)
if nargin < 2, count = 64; end
if nargin < 3, times = linspace(0,1,size(x,1))'; end
assert(size(x,1) >= 8 && all(isfinite(x(:))), 'vault:Quality', 'At least eight finite samples required');
assert(all(diff(times)>0), 'vault:Timing', 'Timestamps must increase');
y = interp1(times, x, linspace(times(1),times(end),count)', 'linear');
end
