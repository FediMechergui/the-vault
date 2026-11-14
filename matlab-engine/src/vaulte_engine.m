function output = vaulte_engine(requestJson)
% Stable JSON boundary for Python Engine and Compiler SDK / MATLAB Runtime.
r = jsondecode(requestJson);
switch string(r.operation)
    case "enroll"
        result = struct('template', enroll_template(r.layer, r.captures));
    case "score"
        switch string(r.layer)
            case "face", result = score_face(r.capture, r.template, r.minimum_score);
            case "body", result = score_body(r.capture, r.template, r.minimum_score);
            case "hand", result = score_hand(r.capture, r.template, r.minimum_score);
            otherwise, error('vault:Layer', 'Unknown layer');
        end
    case "fuse"
        result = fuse_scores(r.results);
    otherwise
        error('vault:Operation', 'Unknown operation');
end
output = jsonencode(result);
end
