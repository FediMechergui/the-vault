function y = unit_shape(x)
y = x - mean(x,1);
s = sqrt(mean(sum(y.^2,2)));
assert(s > 1e-5, 'vault:Quality', 'No meaningful movement detected');
y = y/s;
end
