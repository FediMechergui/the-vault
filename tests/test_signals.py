import numpy as np
import pytest
from vault_core.signals import dtw, smooth, resample, procrustes_distance, LandmarkFilter, unit_shape, cosine_distance
from vault_core.features import body_angles, face_geometry
from vault_core.scoring import enroll, score, fuse_scores, prepare, REPETITIONS
from .samples import capture


def test_dtw_speed_invariance_and_distinct_movement():
    a = np.sin(np.linspace(0, 6, 64))[:, None]
    b = np.sin(np.linspace(0, 6, 70))[:, None]
    assert dtw(a, a) == 0
    assert dtw(a, b) < 0.04
    assert dtw(a, b + 2) > 1


def test_procrustes_removes_translation_scale_rotation_but_not_reflection():
    t = np.linspace(0, 1, 64)
    a = np.column_stack([t, t ** 2 + 0.2 * np.sin(t * 9)])
    rotation = np.array([[0, -1], [1, 0]])
    assert procrustes_distance(a, a @ rotation * 3 + 10) < 1e-10
    assert procrustes_distance(a, a * [1, -1]) > 0.1


@pytest.mark.parametrize('layer', ['face', 'body', 'hand'])
def test_enrollment_and_authentic_repetition(layer):
    template = enroll(layer, [capture(layer, i) for i in range(REPETITIONS[layer])])
    result = score(layer, capture(layer, 0.5), template)
    assert result['passed']
    assert 0.8 <= result['score'] <= 1
    assert template['threshold'] > 0


def test_different_hand_shape_fails():
    template = enroll('hand', [capture('hand', i) for i in range(5)])
    different = capture('hand')
    t = np.linspace(0, 1, 60)
    different['values'] = np.column_stack([0.2 + t * .5, .5 + np.sin(t * 20) * .1, t * 0]).tolist()
    assert not score('hand', different, template)['passed']


def test_missing_tracking_and_stationary_capture_rejected():
    bad = capture('body')
    bad['values'] = np.ones((60, 12)).tolist()
    with pytest.raises(ValueError, match='movement'): prepare('body', bad)
    bad = capture('hand'); bad['times'][20:] = [v + 1000 for v in bad['times'][20:]]
    with pytest.raises(ValueError, match='Tracking'): prepare('hand', bad)


def test_face_needs_expression_and_geometry():
    bad = capture('face'); bad['values'] = np.zeros((60, 52)).tolist()
    with pytest.raises(ValueError, match='expressions'): prepare('face', bad)
    bad = capture('face'); bad['geometry'] = np.zeros((60, 2)).tolist()
    with pytest.raises(ValueError, match='geometry'): prepare('face', bad)


def test_variable_enrollment_rejected():
    samples = [capture('body', i) for i in range(3)]
    samples[1]['values'] = (np.asarray(samples[1]['values']) + 2).tolist()
    with pytest.raises(ValueError, match='different'): enroll('body', samples)


def test_invalid_shapes_times_and_repetitions():
    with pytest.raises(ValueError): resample([[1], [2]])
    with pytest.raises(ValueError): resample(np.ones((8, 1)), times=[0] * 8)
    with pytest.raises(ValueError): smooth(np.full((8, 1), np.nan))
    with pytest.raises(ValueError): dtw(np.zeros((8, 1)), np.zeros((8, 2)))
    with pytest.raises(ValueError): enroll('hand', [capture('hand')])
    with pytest.raises(ValueError): unit_shape(np.ones((8, 2)))
    assert cosine_distance([1, 0], [1, 0]) == 0
    bad = capture('body'); bad['times'] = list(reversed(bad['times']))
    with pytest.raises(ValueError): prepare('body', bad)


def test_fusion_is_and_not_average_only():
    results = [{'layer': 'face', 'score': 1, 'passed': True}, {'layer': 'hand', 'score': .79, 'passed': False}]
    assert not fuse_scores(results)['passed']
    assert fuse_scores(results)['score'] > .8
    with pytest.raises(ValueError): fuse_scores([])


def test_kalman_only_bridges_short_gaps():
    k = LandmarkFilter()
    assert k.update(None) is None
    points = np.ones((21, 3))
    np.testing.assert_allclose(k.update(points), points)
    assert k.update(None) is not None
    assert k.update(None) is not None
    assert k.update(None) is None
    assert k.update(points) is not None


def test_geometric_invariance():
    rng = np.random.default_rng(12)
    pose = rng.random((33, 3))
    np.testing.assert_allclose(body_angles(pose), body_angles(pose * 3 + 2))
    face = rng.random((468, 3))
    np.testing.assert_allclose(face_geometry(face), face_geometry(face * 2 + 3))
    with pytest.raises(ValueError): face_geometry(face[:100])
