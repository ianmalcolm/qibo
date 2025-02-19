"""Test functions defined in `qibo/core/fusion.py`."""
import numpy as np
import pytest
from qibo import gates, K
from qibo.models import Circuit


def test_single_fusion_gate():
    """Check circuit fusion that creates a single ``FusedGate``."""
    queue = [gates.H(0), gates.X(1), gates.CZ(0, 1)]
    c = Circuit(2)
    c.add(queue)
    c = c.fuse()
    assert len(c.queue) == 1
    gate = c.queue[0]
    for gate, target in zip(gate.gates, queue):
        assert gate == target


def test_two_fusion_gate():
    """Check fusion that creates two ``FusedGate``s."""
    queue = [gates.X(0), gates.H(1),
             gates.RX(2, theta=0.1234).controlled_by(1),
             gates.H(2), gates.Y(1),
             gates.H(0)]
    c = Circuit(3)
    c.add(queue)
    c = c.fuse()
    assert len(c.queue) == 2
    gate1, gate2 = c.queue
    if len(gate1.gates) > len(gate2.gates): # pragma: no cover
        # disabling coverage as this may not always happen
        gate1, gate2 = gate2, gate1
    assert gate1.gates == [queue[0], queue[-1]]
    assert gate2.gates == queue[1:-1]


def test_fusedgate_matrix_calculation(backend):
    queue = [gates.H(0), gates.H(1), gates.CNOT(0, 1),
             gates.X(0), gates.X(1)]
    circuit = Circuit(2)
    circuit.add(queue)
    circuit = circuit.fuse()
    assert len(circuit.queue) == 1
    fused_gate = circuit.queue[0]

    x = np.array([[0, 1], [1, 0]])
    h = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    cnot = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1],
                     [0, 0, 1, 0]])
    target_matrix = np.kron(x, x) @ cnot @ np.kron(h, h)
    K.assert_allclose(fused_gate.matrix, target_matrix)


def test_fuse_circuit_two_qubit_gates(backend):
    """Check circuit fusion in circuit with two-qubit gates only."""
    c = Circuit(2)
    c.add(gates.CNOT(0, 1))
    c.add(gates.RX(0, theta=0.1234).controlled_by(1))
    c.add(gates.SWAP(0, 1))
    c.add(gates.fSim(1, 0, theta=0.1234, phi=0.324))
    c.add(gates.RY(1, theta=0.1234).controlled_by(0))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c())


def test_fuse_circuit_three_qubit_gate(backend):
    """Check circuit fusion in circuit with three-qubit gate."""
    c = Circuit(4)
    c.add((gates.H(i) for i in range(4)))
    c.add(gates.CZ(0, 1))
    c.add(gates.CZ(2, 3))
    c.add(gates.TOFFOLI(0, 1, 2))
    c.add(gates.SWAP(1, 2))
    c.add((gates.H(i) for i in range(4)))
    c.add(gates.CNOT(0, 1))
    c.add(gates.CZ(2, 3))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c(), atol=1e-12)


@pytest.mark.parametrize("nqubits", [4, 5, 10, 11])
@pytest.mark.parametrize("nlayers", [1, 2])
def test_variational_layer_fusion(backend, nqubits, nlayers):
    """Check fused variational layer execution."""
    theta = 2 * np.pi * np.random.random((2 * nlayers * nqubits,))
    theta_iter = iter(theta)

    c = Circuit(nqubits)
    for _ in range(nlayers):
        c.add((gates.RY(i, next(theta_iter)) for i in range(nqubits)))
        c.add((gates.CZ(i, i + 1) for i in range(0, nqubits - 1, 2)))
        c.add((gates.RY(i, next(theta_iter)) for i in range(nqubits)))
        c.add((gates.CZ(i, i + 1) for i in range(1, nqubits - 1, 2)))
        c.add(gates.CZ(0, nqubits - 1))

    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c())


@pytest.mark.parametrize("nqubits", [4, 5])
@pytest.mark.parametrize("ngates", [10, 20])
def test_random_circuit_fusion(backend, nqubits, ngates):
    """Check gate fusion in randomly generated circuits."""
    one_qubit_gates = [gates.RX, gates.RY, gates.RZ]
    two_qubit_gates = [gates.CNOT, gates.CZ, gates.SWAP]
    thetas = np.pi * np.random.random((ngates,))
    c = Circuit(nqubits)
    for i in range(ngates):
        gate = one_qubit_gates[int(np.random.randint(0, 3))]
        q0 = np.random.randint(0, nqubits)
        c.add(gate(q0, thetas[i]))
        gate = two_qubit_gates[int(np.random.randint(0, 3))]
        q0, q1 = np.random.randint(0, nqubits, (2,))
        while q0 == q1:
            q0, q1 = np.random.randint(0, nqubits, (2,))
        c.add(gate(q0, q1))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c(), atol=1e-7)


def test_controlled_by_gates_fusion(backend):
    """Check circuit fusion that contains ``controlled_by`` gates."""
    c = Circuit(4)
    c.add((gates.H(i) for i in range(4)))
    c.add(gates.RX(1, theta=0.1234).controlled_by(0))
    c.add(gates.RX(3, theta=0.4321).controlled_by(2))
    c.add((gates.RY(i, theta=0.5678) for i in range(4)))
    c.add(gates.RX(1, theta=0.1234).controlled_by(0))
    c.add(gates.RX(3, theta=0.4321).controlled_by(2))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c())


def test_callbacks_fusion(backend):
    """Check entropy calculation in fused circuit."""
    from qibo import callbacks
    entropy = callbacks.EntanglementEntropy([0])
    c = Circuit(5)
    c.add(gates.H(0))
    c.add(gates.X(1))
    c.add(gates.CallbackGate(entropy))
    c.add(gates.CNOT(0, 1))
    c.add(gates.CallbackGate(entropy))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c())
    target_entropy = [0.0, 1.0, 0.0, 1.0]
    K.assert_allclose(entropy[:], target_entropy, atol=1e-7)


def test_set_parameters_fusion(backend):
    """Check gate fusion when ``circuit.set_parameters`` is used."""
    c = Circuit(2)
    c.add(gates.RX(0, theta=0.1234))
    c.add(gates.RX(1, theta=0.1234))
    c.add(gates.CNOT(0, 1))
    c.add(gates.RY(0, theta=0.1234))
    c.add(gates.RY(1, theta=0.1234))
    fused_c = c.fuse()
    K.assert_allclose(fused_c(), c())

    c.set_parameters(4 * [0.4321])
    fused_c.set_parameters(4 * [0.4321])
    K.assert_allclose(fused_c(), c())
