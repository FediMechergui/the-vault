import pytest
from scripts.evaluate import metrics

def test_perfectly_separated_trials_and_missing_population():
    result=metrics([.95,.9,.2,.1],[True,True,False,False])
    assert result['eer_estimate']==0
    assert result['far_at_080']==0
    assert result['frr_at_080']==0
    with pytest.raises(ValueError):metrics([1,1],[True,True])
