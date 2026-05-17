# SO-101 Hackathon

Team workspace for **SO-101 leader → follower teleoperation** with **[Neuracore](https://neuracore.ai)** data collection, plus **overhead camera** and **Atech.dev** humidity sensing for training.

All project code lives in this repository: [SamFricker/SO-101_Hackathon](https://github.com/SamFricker/SO-101_Hackathon). Do **not** use a separate nested git repo inside `example_so101/`.

---

## What you need

| Item | Purpose |
|------|---------|
| 2× SO-101 arms | Leader (hand-guided) + follower (executes motion) |
| 3× USB connections | Leader, follower, Atech motherboard (each needs its own COM port on Windows) |
| 1–2× USB webcams | Wrist/workspace + overhead scene camera (optional) |
| [Neuracore](https://www.neuracore.com/) account | Login, datasets, recording, training |
| [Atech](https://atech.dev) kit + firmware | Temperature & humidity module (USB serial) |
| Python 3.10+ | 3.10–3.12 recommended; 3.13 works with `feetech-servo-sdk` |

---

## Repository layout

```
SO-101_Hackathon/
├── README.md                 ← you are here
├── example_so101/            ← robot + Neuracore code (from NeuracoreAI/example_so101, extended)
│   ├── examples/
│   │   ├── 1_leader_arm_teleop_so101.py
│   │   └── 2_collect_teleop_data_with_neuracore.py   ← main data-collection script
│   ├── examples/common/configs.py                    ← cameras, humidity defaults
│   └── environment.yaml
├── LICENCE.txt
└── README.txt
```

Upstream reference for the base teleop stack: [NeuracoreAI/example_so101](https://github.com/NeuracoreAI/example_so101).

---

## Step 1 — Get the code (Sam’s repo only)

```powershell
git clone https://github.com/SamFricker/SO-101_Hackathon.git
cd SO-101_Hackathon
```

Work, commit, and push **only** in this folder. If you previously forked `example_so101` on your own GitHub account, ignore that fork for this hackathon.

---

## Step 2 — Python environment

```powershell
cd example_so101
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install feetech-servo-sdk==1.0.0
pip install numpy scipy opencv-python viser yourdfpy neuracore neuracore_types
```

On Windows, if activation is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Optional: `conda env create -f environment.yaml` if you use Conda (note: use `feetech-servo-sdk` instead of `scservo-sdk` on pip).

Run unit tests (no hardware):

```powershell
pip install pytest
python -m pytest tests\ -q
```

---

## Step 3 — One-time SO-101 hardware setup (LeRobot CLI)

Install LeRobot once for motor setup and calibration ([SO-101 docs](https://huggingface.co/docs/lerobot/so101)):

```powershell
# from a lerobot clone
pip install -e ".[feetech]"
```

**Find COM ports** (Device Manager → Ports, or):

```powershell
python -m serial.tools.list_ports
```

**Follower — motor IDs** (before full assembly if possible):

```powershell
lerobot-setup-motors --robot.type=so101_follower --robot.port=COM4
```

**Leader — calibration** (use the same id when running scripts):

```powershell
lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM3 --teleop.id=my_awesome_leader_arm
```

Calibration file path (Windows):

`%USERPROFILE%\.cache\huggingface\lerobot\calibration\teleoperators\so_leader\my_awesome_leader_arm.json`

---

## Step 4 — Atech humidity module

1. Build firmware on [atech.dev](https://atech.dev) with the **Temperature & Humidity** module.
2. Flash over USB (USB transport, **115200 baud**).
3. Plug the Atech board into the PC via USB-C (separate from the robot arms).
4. Close the Atech browser dashboard while recording — only one app should use the serial port.

The board emits JSON lines, for example:

```json
{"type":"sensor","key":"humidity","value":65.2,"module_type":"aht20"}
```

See [Atech module docs](https://atech.dev/docs).

---

## Step 5 — Neuracore login

```powershell
cd example_so101
.\.venv\Scripts\Activate.ps1
neuracore login
```

Follow the prompt and save your API key. Alternatively set `NEURACORE_API_KEY` (see [Neuracore environment variables](https://github.com/NeuracoreAI/neuracore/blob/main/docs/environment_variable.md)).

---

## Step 6 — Configure cameras (optional)

Edit `example_so101/examples/common/configs.py`:

| Setting | Meaning |
|---------|---------|
| `CAMERA_DEVICE_INDEX` | Wrist/workspace webcam (OpenCV index, often `0` or `1`) |
| `OVERHEAD_CAMERA_DEVICE_INDEX` | Overhead scene camera |
| `HUMIDITY_SERIAL_PORT` | Default Atech COM port (can override on CLI) |

Test a webcam without the robot:

```powershell
python scripts\test_camera_thread.py
```

---

## Step 7 — Collect training data

Replace `COM3`, `COM4`, `COM6` with your ports (leader, follower, Atech).

```powershell
cd example_so101
.\.venv\Scripts\Activate.ps1

python examples\2_collect_teleop_data_with_neuracore.py `
  --leader-port COM3 `
  --leader-id my_awesome_leader_arm `
  --follower-port COM4 `
  --follower-id my_awesome_follower_arm `
  --wrist-camera-index 1 `
  --overhead-camera-index 0 `
  --humidity-source atech `
  --humidity-serial-port COM6 `
  --dataset-name so101-demo
```

### What gets streamed to Neuracore

| Data | Neuracore API | Stream name |
|------|---------------|-------------|
| Joint positions | `log_joint_positions` | SO-101 joints |
| Joint targets | `log_joint_target_positions` | SO-101 joints |
| Gripper | `log_parallel_gripper_*` | `gripper` |
| Wrist camera | `log_rgb` | `wrist_camera` |
| Overhead camera | `log_rgb` | `overhead_camera` |
| Humidity (% RH) | `log_custom_1d` | `humidity` |

### Recording episodes

1. Run the script above.
2. Open [neuracore.com](https://www.neuracore.com/) → your dataset **`so101-demo`**.
3. **Start recording** → teleop with the leader → **Stop** episode.
4. Repeat for more episodes.
5. Press **Ctrl+C** in the terminal when finished.

The follower arm is **enabled automatically** at startup. Keep a clear workspace.

### Useful CLI flags

| Flag | Description |
|------|-------------|
| `--wrist-camera-index -1` | Disable wrist camera |
| `--overhead-camera-index -1` | Disable overhead camera |
| `--humidity-source none` | Disable humidity |
| `--humidity-source mock` | Fake humidity (no Atech hardware) |
| `--humidity-serial-baud 115200` | Atech baud rate (default 115200) |

---

## Step 8 — Teleop without Neuracore (debug)

```powershell
python examples\1_leader_arm_teleop_so101.py --real-robot `
  --leader-port COM3 --leader-id my_awesome_leader_arm `
  --follower-port COM4 --follower-id my_awesome_follower_arm
```

---

## Step 9 — Push changes to Sam’s repo

From the **hackathon root** (not inside a nested `.git`):

```powershell
cd SO-101_Hackathon
git status
git add .
git commit -m "Describe your change"
git push origin main
```

Use a branch + pull request if your team prefers review before merging to `main`.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `Calibration file not found` | Run `lerobot-calibrate` with the same `--teleop.id` as `--leader-id` |
| `Failed to open port` | Wrong COM port; close other apps using the port |
| Atech humidity never updates | Correct COM port; close Atech web UI; firmware uses USB @ 115200 |
| No camera frames | Try `--wrist-camera-index 0` or `1`; only one app per camera |
| `scservo-sdk` not found | `pip install feetech-servo-sdk==1.0.0` |
| Repo “inside” another repo | Delete `example_so101\.git` if it reappears; commit files only in `SO-101_Hackathon` |

---

## Safety

This software commands a real robot. Stay clear of the workspace, start with small motions, and use **Ctrl+C** to stop. Read `example_so101/README.md` for more detail on teleop and URDF options.

---

## Links

- [Neuracore docs](https://github.com/NeuracoreAI/neuracore/tree/main/docs)
- [Neuracore SO-101 example](https://github.com/NeuracoreAI/example_so101)
- [LeRobot SO-101](https://huggingface.co/docs/lerobot/so101)
- [Atech.dev docs](https://atech.dev/docs)
