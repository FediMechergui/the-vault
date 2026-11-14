function result = score_face(capture,template,minimumScore)
if nargin<3, minimumScore=0.8; end
result=score_layer('face',capture,template,minimumScore);
end
