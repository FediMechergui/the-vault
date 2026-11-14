function result = fuse_scores(results)
assert(~isempty(results),'vault:Scores','At least one layer is required');
if iscell(results), results=[results{:}]; end
result=struct('passed',all([results.passed]),'score',mean([results.score]));
end
