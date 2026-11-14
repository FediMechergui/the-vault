function result = score_body(capture,template,minimumScore)
if nargin<3, minimumScore=0.8; end
result=score_layer('body',capture,template,minimumScore);
end
