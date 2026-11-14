function result = score_layer(layer,capture,template,minimumScore)
assert(string(template.layer)==string(layer) && template.version==1,'vault:Template','Incompatible template');
candidate=prepare_capture(layer,capture);
distances=zeros(numel(template.samples),1);
for i=1:numel(template.samples)
    if iscell(template.samples), sample=template.samples{i}; else, sample=template.samples(i); end
    distances(i)=layer_distance(layer,candidate,sample);
end
d=median(distances); ratio=d/template.threshold;
score=max(0,min(1,1-0.2*ratio));
result=struct('score',score,'confidence',min(1,numel(capture.times)/30), ...
    'passed',ratio<=1 && score>=minimumScore, ...
    'details',struct('distance',d,'threshold',template.threshold,'ratio',ratio));
end
