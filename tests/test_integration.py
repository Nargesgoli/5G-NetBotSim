"""Checks that do not require Docker, ROS, or an attached cellular network."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
import csv

ROOT = Path(__file__).resolve().parents[1]


def load_script(relative):
    fake_zmq = types.SimpleNamespace(Context=object)
    spec = importlib.util.spec_from_file_location('checked_script', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'zmq': fake_zmq}):
        spec.loader.exec_module(module)
    return module


class IntegrationTests(unittest.TestCase):
    def test_teleoperation_route_agrees_at_both_ends(self):
        for value in ['5012', '5500']:
            with patch.dict(os.environ, {'NETBOTSIM_TELEOP_PORT': value}):
                bridge = load_script('BotSim/examples/ground_teleoperation/ran_bridge.py')
                receiver = load_script('BotSim/examples/ground_teleoperation/ue_receiver.py')
            for cfg in receiver.UE_CONFIG:
                self.assertEqual(bridge.UE_ROUTES[cfg['ns_name'].encode()],
                                 (cfg['bind_ip'], cfg['udp_port']))

    def test_commander_socket_has_one_thread_owner(self):
        module = load_script('BotSim/examples/ground_teleoperation/commander.py')
        owner = threading.get_ident()
        sent = []

        class Pub:
            def bind(self, endpoint): pass
            def send_multipart(self, frames):
                self_owner = threading.get_ident()
                if self_owner != owner:
                    raise AssertionError('PUB socket used by another thread')
                sent.append(frames)
            def close(self): pass

        pub = Pub()
        ctx = types.SimpleNamespace(socket=lambda *_: pub, term=lambda: None)
        module.zmq = types.SimpleNamespace(Context=lambda: ctx, PUB=1)
        with patch.object(module.time, 'sleep', lambda _: None):
            module.main()
        self.assertEqual(len(sent), 2 * len(module.COMMAND_PAIRS))
        self.assertEqual([f[0] for f in sent], [b'ue1', b'ue2'] * 4)

    def test_namespace_permission_failure_is_not_ignored(self):
        for relative in ['BotSim/examples/ground_teleoperation/ue_receiver.py',
                         'BotSim/examples/ground_velocity_replay/ue1_injector.py',
                         'BotSim/examples/ground_velocity_replay/ue2_receiver.py',
                         'BotSim/robot_to_robot/ue1_injector.py',
                         'BotSim/robot_to_robot/ue2_receiver.py']:
            module = load_script(relative)
            with tempfile.TemporaryDirectory() as directory:
                original = Path(directory) / 'original'
                target = Path(directory) / 'target'
                original.touch(); target.touch()
                actual_open = open
                def namespace_open(path, *args, **kwargs):
                    chosen = original if str(path) == '/proc/thread-self/ns/net' else target
                    return actual_open(chosen, *args, **kwargs)
                with patch('builtins.open', namespace_open), \
                     patch.object(module, '_setns', lambda *_: -1), \
                     patch.object(module, 'get_errno', lambda: 1):
                    with self.assertRaises(PermissionError):
                        module.enter_ns('test_ue')

    def test_drone_packet_route_preserves_state_and_drops_stale_packets(self):
        from unittest.mock import Mock
        stamp = 2_000_000_000
        state = b'1.0,2.0,3.0,0.5'
        injector = load_script('BotSim/robot_to_robot/ue1_injector.py')
        sub, udp = Mock(), Mock()
        sub.recv_multipart.side_effect = [
            [b'leader', b'1,2000000000', state],
            [b'leader', b'2,0', state], KeyboardInterrupt]
        ctx = Mock()
        ctx.socket.return_value = sub
        injector.zmq = types.SimpleNamespace(Context=lambda: ctx, SUB=1,
            RCVHWM=2, SUBSCRIBE=3)
        with patch.object(injector.os.path, 'exists', return_value=True), \
             patch.object(injector, 'enter_ns', return_value=Mock()), \
             patch.object(injector.socket, 'socket', return_value=udp), \
             patch.object(injector.time, 'sleep'), \
             patch.object(injector.time, 'monotonic_ns', return_value=stamp):
            injector.main()
        datagram = b'1,2000000000|' + state
        udp.sendto.assert_called_once_with(datagram, ('172.16.0.3', 6000))
        receiver = load_script('BotSim/robot_to_robot/ue2_receiver.py')
        pub, incoming = Mock(), Mock()
        incoming.recvfrom.side_effect = [(datagram, ('172.16.0.2', 1)),
            (b'2,0|' + state, ('172.16.0.2', 1)), KeyboardInterrupt]
        ctx = Mock()
        ctx.socket.return_value = pub
        receiver.zmq = types.SimpleNamespace(Context=lambda: ctx, PUB=1, SNDHWM=2)
        with patch.object(receiver.os.path, 'exists', return_value=True), \
             patch.object(receiver, 'enter_ns', return_value=Mock()), \
             patch.object(receiver.socket, 'socket', return_value=incoming), \
             patch.object(receiver.time, 'sleep'), \
             patch.object(receiver.time, 'monotonic_ns', return_value=stamp):
            receiver.main()
        incoming.bind.assert_called_once_with(('172.16.0.3', 6000))
        pub.send_string.assert_called_once_with(state.decode())

    def test_drone_plot_rejects_header_only_results(self):
        module = load_script('experiments/robot_to_robot/plot_tracking_error.py')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'follower.csv'
            path.write_text('t_sec,fx,fy,fz,lx,ly,lz,error\n')
            with self.assertRaisesRegex(ValueError, 'contains no samples'):
                module.load_follower(path)
            path.write_text('t_sec,fx,fy,fz,lx,ly,lz,error\n0,0,0,1,2,0,1,0\n')
            self.assertEqual(module.load_follower(path)[0]['error'], 0.)

    def test_network_launcher_resolves_paths_and_preserves_ue_arguments(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'project'
            (project / 'scripts').mkdir(parents=True)
            shutil.copy2(ROOT / 'scripts/run-network', project / 'scripts/run-network')
            stack = project / 'vendor/network-stack'
            (stack / '.config').mkdir(parents=True)
            paths = {'epc': 'srsran-enb/build/srsepc/src/srsepc',
                     'enb': 'srsran-enb/build/srsenb/src/srsenb',
                     'ue1': 'srsran-ue/build/srsue/src/srsue',
                     'ue2': 'srsran-ue/build/srsue/src/srsue2'}
            for role, binary_path in paths.items():
                binary = stack / binary_path
                binary.parent.mkdir(parents=True, exist_ok=True)
                binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
                binary.chmod(0o755)
                (stack / '.config' / f'{role}.conf').touch()
            for name in ['params1.txt', 'params2.txt']:
                (stack / 'srsran-ue' / name).touch()
            for role in paths:
                result = subprocess.run(['bash', str(project / 'scripts/run-network'), role],
                                        cwd=directory, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(str(stack / '.config' / f'{role}.conf'), result.stdout)
                if role.startswith('ue'):
                    self.assertIn('--gw.netns=' + role, result.stdout)
                    self.assertIn('--params_filename=../params' + role[-1] + '.txt', result.stdout)
                    self.assertIn('base_srate=23.04e6', result.stdout)

    def test_udp_timing_receivers_write_real_packet_csv(self):
        for name in ['ue1', 'ue2']:
            with tempfile.TemporaryDirectory() as directory:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                    probe.bind(('127.0.0.1', 0))
                    port = probe.getsockname()[1]
                proc = subprocess.Popen([sys.executable,
                    str(ROOT / f'experiments/human_to_robot/timing/{name}_receiver.py'),
                    '--name', name.upper(), '--port', str(port), '--out', 'capture.csv'],
                    cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                        deadline = time.monotonic() + 5
                        records = []
                        while time.monotonic() < deadline:
                            stamp = time.monotonic_ns()
                            packet = f'7,{stamp-3000},{stamp-2000},{stamp-1000}|forward'.encode()
                            sender.sendto(packet, ('127.0.0.1', port))
                            time.sleep(.05)
                            path = Path(directory) / 'capture.csv'
                            if path.exists():
                                with path.open() as source:
                                    records = list(csv.DictReader(source))
                            if records: break
                        self.assertTrue(records, 'receiver never captured a UDP datagram')
                        row = records[0]
                        self.assertEqual(row['seq'], '7')
                        self.assertEqual(row['payload_bytes'], '7')
                        self.assertEqual(float(row['ubuntu_to_gnb_us']), 1.)
                        self.assertEqual(float(row['gnb_proc_us']), 1.)
                        self.assertAlmostEqual(float(row['total_us']),
                            2 + float(row['gnb_to_ue_us']), places=6)
                finally:
                    proc.terminate()
                    proc.communicate(timeout=5)

    def test_plot_requires_logs_and_marks_explicit_demo(self):
        if not all(importlib.util.find_spec(m) for m in ['numpy', 'pandas', 'matplotlib', 'scipy']):
            self.skipTest('plot dependencies unavailable')
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ, MPLBACKEND='Agg')
            base = [sys.executable, str(ROOT / 'BotSim/examples/ground_velocity_replay/plot_separation.py')]
            missing = subprocess.run(base + ['--save'], cwd=directory,
                env=environment, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('Missing experiment log', missing.stderr)
            self.assertFalse((Path(directory) / 'platooning_trajectories.png').exists())
            demo = subprocess.run(base + ['--demo', '--save'], cwd=directory,
                env=environment, capture_output=True, text=True)
            self.assertEqual(demo.returncode, 0, demo.stderr)
            self.assertTrue((Path(directory) / 'synthetic_demo.png').exists())
            self.assertFalse((Path(directory) / 'platooning_trajectories.png').exists())


if __name__ == '__main__':
    unittest.main()
