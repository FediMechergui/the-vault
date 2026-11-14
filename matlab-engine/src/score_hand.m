function result = score_hand(capture,template,minimumScore)
if nargin<3, minimumScore=0.8; end
result=score_layer('hand',capture,template,minimumScore);
end
