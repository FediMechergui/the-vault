function result = prepare_capture(layer,capture)
t = capture.times(:)/1000;
x = capture.values;
assert(size(x,1)>=8 && all(isfinite(x(:))) && all(isfinite(t)), 'vault:Quality', 'Insufficient finite samples');
assert(length(t)==size(x,1) && all(diff(t)>0), 'vault:Timing', 'Invalid capture timing');
assert(max(diff(t))<=0.4, 'vault:Quality', 'Tracking lost for too long; please retry');
duration = t(end)-t(1);
switch string(layer)
    case "face", limits=[1.2,4.5]; dims=52;
    case "body", limits=[3,6.5]; dims=12;
    case "hand", limits=[0.7,8]; dims=3;
    otherwise, error('vault:Layer','Unknown layer');
end
assert(duration>=limits(1) && duration<=limits(2), 'vault:Quality', 'Capture duration out of range');
assert(size(x,2)==dims,'vault:Quality','Incorrect feature dimensions');
x = resample_signal(x,max(8,round(duration*15)),t);
x = sgolayfilt(x,2,7);
dt = duration/(size(x,1)-1);
switch string(layer)
    case "hand"
        assert(norm(max(x(:,1:2))-min(x(:,1:2)))>=0.06,'vault:Quality','Draw a larger signature');
        centered = unit_shape(x(:,1:2));
        velocity = time_gradient(centered,dt);
        speed = vecnorm(velocity,2,2);
        acceleration = time_gradient(speed,dt);
        result = struct('shape',resample_signal(centered),'signal',resample_signal([speed/10,acceleration/100]),'duration',duration);
    case "body"
        assert(max(std(x,1,1))>=0.025,'vault:Quality','Add a clear body movement');
        result = struct('signal',resample_signal([x,time_gradient(x,dt)/5]),'duration',duration);
    case "face"
        assert(max(max(x)-min(x))>=0.12,'vault:Quality','Perform your two expressions clearly');
        g = capture.geometry;
        assert(isequal(size(g),[length(t),60]) && all(isfinite(g(:))), 'vault:Quality','Invalid face geometry');
        result = struct('signal',resample_signal(x),'geometry',median(g,1),'duration',duration);
end
end

function d = time_gradient(x,dt)
d = zeros(size(x));
d(1,:)=(x(2,:)-x(1,:))/dt;
d(end,:)=(x(end,:)-x(end-1,:))/dt;
d(2:end-1,:)=(x(3:end,:)-x(1:end-2,:))/(2*dt);
end
