function template = enroll_template(layer,captures)
switch string(layer)
    case "face", required=2; bounds=[0.025,0.18];
    case "body", required=3; bounds=[0.035,0.22];
    case "hand", required=5; bounds=[0.04,0.32];
    otherwise, error('vault:Layer','Unknown layer');
end
assert(numel(captures)==required,'vault:Quality','Incorrect number of repetitions');
samples=cell(1,required);
for i=1:required
    if iscell(captures), c=captures{i}; else, c=captures(i); end
    samples{i}=prepare_capture(layer,c);
end
pairs=nchoosek(1:required,2); distances=zeros(size(pairs,1),1);
for i=1:size(pairs,1)
    distances(i)=layer_distance(layer,samples{pairs(i,1)},samples{pairs(i,2)});
end
mu=mean(distances); sigma=std(distances,1);
assert(mu+2*sigma<=bounds(2),'vault:Quality','Repetitions are too different; record a more consistent gesture');
template=struct('version',1,'layer',layer,'samples',{samples},'threshold',max(bounds(1),min(bounds(2),mu+2*sigma)), 'mu',mu,'sigma',sigma);
end
