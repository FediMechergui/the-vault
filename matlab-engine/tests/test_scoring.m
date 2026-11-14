function tests = test_scoring
tests = functiontests(localfunctions);
end
function testIdenticalDTW(testCase)
a=sin(linspace(0,6,64)');
verifyEqual(testCase,dtw_distance(a,a),0,'AbsTol',1e-12);
end
function testShapeTransform(testCase)
t=linspace(0,1,64)';
a=struct('shape',[t,t.^2+0.2*sin(t*9)],'signal',zeros(64,2));
b=a;b.shape=a.shape*[0,-1;1,0]*3+10;
verifyLessThan(testCase,layer_distance('hand',a,b),1e-10);
end
function testAndFusion(testCase)
r=[struct('score',1,'passed',true),struct('score',0.79,'passed',false)];
result=fuse_scores(r);
verifyFalse(testCase,result.passed);
end
