function d = layer_distance(layer,a,b)
temporal = dtw_distance(a.signal,b.signal);
switch string(layer)
    case "hand"
        aa = unit_shape(resample_signal(a.shape));
        bb = unit_shape(resample_signal(b.shape));
        % Procrustes with rotation but without reflection or additional scale.
        [~,aligned] = procrustes(bb,aa,'Scaling',false,'Reflection',false);
        shape = sqrt(mean(sum((aligned-bb).^2,2)));
        d = 0.4*shape + 0.6*temporal;
    case "face"
        aa=a.geometry(:); bb=b.geometry(:);
        geometry=max(0,min(2,1-dot(aa,bb)/max(norm(aa)*norm(bb),1e-9)));
        d = 0.45*min(geometry*10,1) + 0.55*temporal;
    otherwise
        d = temporal;
end
end
