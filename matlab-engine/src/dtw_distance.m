function d = dtw_distance(a,b)
% Multivariate RMS local cost; path-length normalization, 10% Sakoe-Chiba band.
n = size(a,1); m = size(b,1);
assert(size(a,2)==size(b,2), 'vault:Dimensions', 'Feature dimensions differ');
band = max(abs(n-m),ceil(max(n,m)*0.1));
costs = inf(n+1,m+1); lengths = zeros(n+1,m+1); costs(1,1)=0;
for i=1:n
    for j=max(1,i-band):min(m,i+band)
        previous = [costs(i,j),costs(i,j+1),costs(i+1,j)];
        [best,k] = min(previous);
        plen = [lengths(i,j),lengths(i,j+1),lengths(i+1,j)];
        costs(i+1,j+1) = best + sqrt(mean((a(i,:)-b(j,:)).^2));
        lengths(i+1,j+1) = plen(k)+1;
    end
end
d = costs(end,end)/max(lengths(end,end),1);
end
