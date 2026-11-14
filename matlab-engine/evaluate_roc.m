function report = evaluate_roc(csvPath)
% Input must contain held-out, consented trials: layer,genuine,score,latency_ms.
t=readtable(csvPath,'TextType','string');
layers=unique(t.layer); report=struct();
figure('Name','THE VAULT — held-out biometric evaluation');
tiledlayout(1,numel(layers));
for layer=layers'
    rows=t(t.layer==layer,:); genuine=rows.genuine==1;
    assert(any(genuine) && any(~genuine),'Need genuine and impostor attempts');
    thresholds=[-eps;unique(rows.score);1+eps];far=zeros(size(thresholds));frr=far;
    for i=1:numel(thresholds)
        far(i)=mean(rows.score(~genuine)>=thresholds(i));
        frr(i)=mean(rows.score(genuine)<thresholds(i));
    end
    [~,index]=min(abs(far-frr));
    report.(layer)=struct('eerEstimate',(far(index)+frr(index))/2,'threshold',thresholds(index), ...
        'latencyP50',median(rows.latency_ms),'latencyP95',prctile(rows.latency_ms,95));
    nexttile;plot(far,1-frr,'LineWidth',2);xlabel('False acceptance rate');ylabel('True acceptance rate');
    title(layer);grid on;axis square;
end
end
