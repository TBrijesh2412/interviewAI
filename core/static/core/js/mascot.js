/**
 * 3D Cute AI Orb Mascot — Pure Canvas 2D
 * Replaces the fox with a beautiful, floating, glowing robot sphere.
 * Features:
 *  - Floating animation (hovering sine wave)
 *  - Interactive 3D orbiting rings
 *  - Expressive glowing eyes that track the cursor softly
 *  - Translucent glassmorphism body
 */
(function () {
    const canvas = document.getElementById('fox-canvas');
    if (!canvas) return;

    const W = 360, H = 400;
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    // Global style for the canvas
    canvas.style.filter = "drop-shadow(0 0 30px rgba(232, 112, 26, 0.3))";

    // --- State & Mouse Tracking ---
    let tRX = 0, tRY = 0;
    let cRX = 0, cRY = 0;
    let time = 0;
    let blinkTimer = 0;
    let isBlinking = false;

    // Idle State
    let lastMoveTime = Date.now();
    let idleRX = 0, idleRY = 0;
    let nextIdleAction = 0;

    window.addEventListener('mousemove', e => {
        lastMoveTime = Date.now();
        const rect = canvas.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        // Much smaller range and less sensitivity
        tRY = Math.max(-0.2, Math.min(0.2, dx / 1000));
        tRX = Math.max(-0.15, Math.min(0.15, -dy / 1000));
    });

    // --- 3D Math Helpers ---
    function rotY(p, ang) {
        const c = Math.cos(ang), s = Math.sin(ang);
        return [p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c];
    }
    function rotX(p, ang) {
        const c = Math.cos(ang), s = Math.sin(ang);
        return [p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c];
    }
    function rotZ(p, ang) {
        const c = Math.cos(ang), s = Math.sin(ang);
        return [p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]];
    }

    function project(p, floatOffset = 0) {
        const FOV = 4.5;
        const CAM_Z = 4.0;
        const z = p[2] + CAM_Z;
        const scale = (FOV / z) * 130;
        return [
            (W / 2) + p[0] * scale,
            (H / 2) + (p[1] + floatOffset) * scale,
            scale // return scale for sizing circles
        ];
    }

    // --- Drawing Components ---

    function drawBody(floatOffset) {
        const center = project([0, 0, 0], floatOffset);
        const r = 85;

        // 1. Ambient Body Glow
        const glow = ctx.createRadialGradient(center[0], center[1], r * 0.7, center[0], center[1], r * 1.8);
        glow.addColorStop(0, 'rgba(232, 112, 26, 0.15)');
        glow.addColorStop(1, 'rgba(232, 112, 26, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(center[0], center[1], r * 1.8, 0, Math.PI * 2);
        ctx.fill();

        // 2. Main Sphere with Fresnel/Rim Light Effect
        const grad = ctx.createRadialGradient(
            center[0] - r * 0.3, center[1] - r * 0.3, 0,
            center[0], center[1], r
        );
        grad.addColorStop(0, '#FFF5F0'); // Soft white center
        grad.addColorStop(0.4, '#FFE0D0'); // Cream
        grad.addColorStop(0.8, '#E8701A'); // Brand Orange
        grad.addColorStop(1, '#5C150B');   // Dark Rim

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(center[0], center[1], r, 0, Math.PI * 2);
        ctx.fill();

        // 3. Glassy Reflection
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        const reflect = ctx.createLinearGradient(center[0], center[1] - r, center[0], center[1]);
        reflect.addColorStop(0, 'rgba(255,255,255,0.4)');
        reflect.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = reflect;
        ctx.beginPath();
        ctx.ellipse(center[0], center[1] - r * 0.4, r * 0.7, r * 0.5, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // 4. Internal Glowing Core (AI Brain)
        const coreSize = 15 + Math.sin(time * 3) * 3;
        const corePulse = 0.5 + Math.sin(time * 3) * 0.2;
        ctx.shadowColor = '#FF9D5C';
        ctx.shadowBlur = 20;
        ctx.fillStyle = `rgba(255, 255, 255, ${corePulse})`;
        ctx.beginPath();
        // Drawing a small diamond-ish shape
        ctx.moveTo(center[0], center[1] - coreSize);
        ctx.lineTo(center[0] + coreSize, center[1]);
        ctx.lineTo(center[0], center[1] + coreSize);
        ctx.lineTo(center[0] - coreSize, center[1]);
        ctx.closePath();
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    function drawEars(floatOffset) {
        // Fox ears in 3D
        const earPoints = [
            // Left Ear [x, y, z]
            [[-0.3, -0.6, 0], [-0.65, -1.2, -0.1], [-0.85, -0.4, 0.1]],
            // Right Ear
            [[0.3, -0.6, 0], [0.65, -1.2, -0.1], [0.85, -0.4, 0.1]]
        ];

        earPoints.forEach((tri, i) => {
            const pts = tri.map(p => {
                let r = rotX(rotY(p, cRY), cRX);
                return { prj: project(r, floatOffset), z: r[2] };
            });

            // Sort-of primitive culling: only draw if reasonable Z
            const avgZ = (pts[0].z + pts[1].z + pts[2].z) / 3;

            ctx.beginPath();
            ctx.moveTo(pts[0].prj[0], pts[0].prj[1]);
            ctx.lineTo(pts[1].prj[0], pts[1].prj[1]);
            ctx.lineTo(pts[2].prj[0], pts[2].prj[1]);
            ctx.closePath();

            // Ear Material (Gradient for fluff/depth)
            const g = ctx.createLinearGradient(pts[0].prj[0], pts[0].prj[1], pts[1].prj[0], pts[1].prj[1]);
            g.addColorStop(0, '#E8701A');
            g.addColorStop(1, '#FFA86B');
            ctx.fillStyle = g;
            ctx.fill();

            // Inner ear detail
            ctx.strokeStyle = 'rgba(0,0,0,0.1)';
            ctx.lineWidth = 1;
            ctx.stroke();
        });
    }

    function drawEyes(floatOffset) {
        const leftEye3D = [-0.3, -0.12, 0.88];
        const rightEye3D = [0.3, -0.12, 0.88];

        const rL = rotX(rotY(leftEye3D, cRY), cRX);
        const rR = rotX(rotY(rightEye3D, cRY), cRX);

        if (rL[2] > 0) drawSingleEye(project(rL, floatOffset), -cRY);
        if (rR[2] > 0) drawSingleEye(project(rR, floatOffset), -cRY);

        // Smile
        const mouth3D = [0, 0.15, 0.95];
        const rM = rotX(rotY(mouth3D, cRY), cRX);
        if (rM[2] > 0) {
            const pM = project(rM, floatOffset);
            ctx.strokeStyle = '#3D0E06';
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.arc(pM[0], pM[1], 10, 0.2, Math.PI - 0.2);
            ctx.stroke();
        }
    }

    function drawSingleEye(p, tilt) {
        const [ex, ey, s] = p;
        const eyeW = 14 * (s / 130);
        const eyeH = isBlinking ? 2 : 18 * (s / 130);

        ctx.fillStyle = '#1A0603';
        ctx.beginPath();
        ctx.ellipse(ex, ey, eyeW, eyeH, tilt * 0.3, 0, Math.PI * 2);
        ctx.fill();

        if (!isBlinking) {
            // Glow
            ctx.fillStyle = '#FF9D5C';
            ctx.beginPath();
            ctx.ellipse(ex, ey + 4, eyeW * 0.6, eyeH * 0.5, tilt * 0.3, 0, Math.PI * 2);
            ctx.fill();

            // Catchlight
            ctx.fillStyle = '#FFF';
            ctx.beginPath();
            ctx.arc(ex - eyeW * 0.3, ey - eyeH * 0.3, 4, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function drawRings(floatOffset, drawBack) {
        // Orbit rings - refined colors
        const rings = [
            { r: 1.5, tiltX: 0.5, tiltZ: 0.3, speed: 0.8, color: '#c97fea', glow: '#b060d0' },  // Purple
            { r: 1.9, tiltX: -0.4, tiltZ: 0.6, speed: -0.6, color: '#E8701A', glow: '#ff7c30' }, // Orange
            { r: 2.3, tiltX: 0.2, tiltZ: -0.4, speed: 0.4, color: '#2ecc71', glow: '#27ae60' }  // Green
        ];

        rings.forEach(ring => {
            const pts = [];
            const segments = 60;
            for (let i = 0; i <= segments; i++) {
                const a = (i / segments) * Math.PI * 2 + (time * ring.speed);
                let p = [Math.cos(a) * ring.r, 0, Math.sin(a) * ring.r];
                p = rotX(p, ring.tiltX);
                p = rotZ(p, ring.tiltZ);
                p = rotY(p, cRY);
                p = rotX(p, cRX);
                pts.push({ prj: project(p, floatOffset), z: p[2] });
            }

            // Draw in segments to handle depth
            for (let i = 0; i < segments; i++) {
                const p1 = pts[i];
                const p2 = pts[i + 1];
                const isBack = (p1.z + p2.z) / 2 < 0;

                if (isBack === drawBack) {
                    ctx.beginPath();
                    ctx.moveTo(p1.prj[0], p1.prj[1]);
                    ctx.lineTo(p2.prj[0], p2.prj[1]);
                    ctx.strokeStyle = ring.color;
                    ctx.lineWidth = isBack ? 1 : 2.5;
                    ctx.globalAlpha = isBack ? 0.3 : 0.8;
                    if (!isBack) {
                        ctx.shadowColor = ring.glow;
                        ctx.shadowBlur = 10;
                    }
                    ctx.stroke();
                    ctx.shadowBlur = 0;
                    ctx.globalAlpha = 1.0;
                }
            }

            // Glowing data packet on front
            if (!drawBack) {
                const pNode = pts[0];
                if (pNode.z > 0) {
                    ctx.fillStyle = '#fff';
                    ctx.shadowColor = ring.glow;
                    ctx.shadowBlur = 15;
                    ctx.beginPath();
                    ctx.arc(pNode.prj[0], pNode.prj[1], 4, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.shadowBlur = 0;
                }
            }
        });
    }

    const particles = Array.from({ length: 12 }, () => ({
        x: (Math.random() - 0.5) * 6,
        y: (Math.random() - 0.5) * 6,
        z: (Math.random() - 0.5) * 6,
        size: Math.random() * 0.15 + 0.05,
        color: Math.random() > 0.6 ? '#c97fea' : '#E8701A',
        rx: Math.random() * Math.PI,
        ry: Math.random() * Math.PI,
        rz: Math.random() * Math.PI,
        rv: (Math.random() - 0.5) * 0.04 // rotation velocity
    }));

    function drawParticles(floatOffset) {
        particles.forEach(p => {
            // Drift & Spin
            p.y -= 0.002; if (p.y < -3) p.y = 3;
            p.rx += p.rv; p.ry += p.rv;

            // Project box vertices
            const s = p.size;
            const verts = [
                [-s, -s, 0], [s, -s, 0], [s, s, 0], [-s, s, 0]
            ].map(v => {
                let r = rotZ(rotY(rotX(v, p.rx), p.ry), p.rz);
                r[0] += p.x; r[1] += p.y; r[2] += p.z;
                // Mascot rotation
                r = rotX(rotY(r, cRY), cRX);
                return project(r, floatOffset);
            });

            const avgZ = rotX(rotY([p.x, p.y, p.z], cRY), cRX)[2];
            const alpha = Math.max(0, (avgZ + 3) / 6);

            ctx.fillStyle = p.color;
            ctx.globalAlpha = alpha * 0.5;
            ctx.beginPath();
            ctx.moveTo(verts[0][0], verts[0][1]);
            verts.slice(1).forEach(v => ctx.lineTo(v[0], v[1]));
            ctx.closePath();
            ctx.fill();

            // Add a little glow to the boxies
            ctx.shadowColor = p.color;
            ctx.shadowBlur = 10 * alpha;
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 0.5;
            ctx.stroke();
            ctx.shadowBlur = 0;
            ctx.globalAlpha = 1.0;
        });
    }

    // Mood/Expression State
    let mood = 'neutral';
    let nextMoodChange = 0;

    function frame() {
        requestAnimationFrame(frame);
        time += 0.012;

        const now = Date.now();
        const isIdle = (now - lastMoveTime) > 5000;

        // Mood Logic
        if (now > nextMoodChange) {
            const moods = ['neutral', 'neutral', 'happy', 'curious'];
            mood = moods[Math.floor(Math.random() * moods.length)];
            nextMoodChange = now + 3000 + Math.random() * 5000;
        }

        if (isIdle) {
            if (now > nextIdleAction) {
                // Think of a new spot - EXTREMELY SUBTLE
                idleRY = (Math.random() - 0.5) * 0.15;
                idleRX = (Math.random() - 0.5) * 0.1;
                nextIdleAction = now + 5000 + Math.random() * 5000;
            }
            cRY = cRY + (idleRY - cRY) * 0.01;
            cRX = cRX + (idleRX - cRX) * 0.01;
        } else {
            cRY = cRY + (tRY - cRY) * 0.1;
            cRX = cRX + (tRX - cRX) * 0.1;
        }

        blinkTimer--;
        if (blinkTimer <= 0) {
            isBlinking = !isBlinking;
            blinkTimer = isBlinking ? 8 : 120 + Math.random() * 200;
        }

        // Smaller floating amplitude (0.05 instead of 0.12)
        const floatOffset = Math.sin(time * 1.5) * 0.05;

        ctx.clearRect(0, 0, W, H);

        drawParticles(floatOffset);
        drawRings(floatOffset, true); // Back rings
        drawEars(floatOffset);
        drawBody(floatOffset);
        drawEyes(floatOffset);
        drawRings(floatOffset, false); // Front rings
    }

    function drawSingleEye(p, tilt) {
        const [ex, ey, s] = p;
        const eyeW = 14 * (s / 130);
        const eyeH = isBlinking ? 2 : 18 * (s / 130);

        ctx.save();
        ctx.translate(ex, ey);
        ctx.rotate(tilt * 0.3);

        if (mood === 'happy' && !isBlinking) {
            // Drawn as upward arcs ^ ^
            ctx.strokeStyle = '#1A0603';
            ctx.lineWidth = 5;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.arc(0, 5, eyeW, Math.PI + 0.2, -0.2);
            ctx.stroke();
        } else {
            ctx.fillStyle = '#1A0603';
            ctx.beginPath();
            ctx.ellipse(0, 0, eyeW, eyeH, 0, 0, Math.PI * 2);
            ctx.fill();

            if (!isBlinking) {
                // Glow
                ctx.fillStyle = mood === 'curious' ? '#60A5FA' : '#FF9D5C';
                ctx.beginPath();
                ctx.ellipse(0, 4, eyeW * 0.6, eyeH * 0.5, 0, 0, Math.PI * 2);
                ctx.fill();

                // Catchlight
                ctx.fillStyle = '#FFF';
                ctx.beginPath();
                ctx.arc(-eyeW * 0.3, -eyeH * 0.3, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
    }

    frame();
})();
