/**
 * Grid World Renderer for Preference Trials
 */
class PreferenceGridWorldRenderer {
    constructor(canvas, config = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        const pixelRatio = window.devicePixelRatio || 1;

        this.config = {
            laneLength: 11,
            maxWidth: 900,
            laneHeight: 100,
            laneColor: '#ddd',
            animationSpeed: 600,
            horizontalBorder: 80,
            verticalBorder: 50,
            pixelRatio: pixelRatio,
            imageBasePath: 'images',
            ...config
        };

        // Calculate cell size and scale factor
        this.config.cellSize = Math.floor((this.config.maxWidth - 2 * this.config.horizontalBorder) / this.config.laneLength);
        this.config.scaleFactor = this.config.maxWidth / 1200;

        const displayWidth = this.config.laneLength * this.config.cellSize + 2 * this.config.horizontalBorder + 200;
        const displayHeight = this.config.laneHeight + Math.round(320 * this.config.scaleFactor) + 2 * this.config.verticalBorder;

        this.canvas.style.width = `${displayWidth}px`;
        this.canvas.style.height = `${displayHeight}px`;
        this.canvas.width = displayWidth * pixelRatio;
        this.canvas.height = displayHeight * pixelRatio;

        this.ctx.scale(pixelRatio, pixelRatio);
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';

        this.displayWidth = displayWidth;
        this.displayHeight = displayHeight;

        // Animation state
        this.animationFrame = null;
        this.isAnimating = false;

        // Image cache
        this.images = new Map();
        // Load images happens in experiment.js usually via preloader, but we can set them here too if passed
    }

    drawLane() {
        const { laneLength, cellSize, laneHeight, laneColor, verticalBorder, scaleFactor } = this.config;

        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

        const laneWidth = laneLength * cellSize;
        const laneX = (this.displayWidth - laneWidth) / 2;
        // Reduce top offset to 40 (was 160) to actually remove top margin
        const laneY = verticalBorder + Math.round(40 * scaleFactor);

        this.ctx.strokeStyle = laneColor;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(laneX, laneY, laneWidth, laneHeight - 20);

        this.ctx.lineWidth = 1;
        for (let i = 1; i < laneLength; i++) {
            const dividerX = laneX + i * cellSize;
            this.ctx.beginPath();
            this.ctx.moveTo(dividerX, laneY);
            this.ctx.lineTo(dividerX, laneY + laneHeight - 20);
            this.ctx.stroke();
        }

        this.laneX = laneX;
    }

    drawEntity(entity) {
        if (entity.type === 'wizard') return;

        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const laneY = verticalBorder + Math.round(40 * scaleFactor);
        const x = this.laneX + entity.position * cellSize;
        const y = laneY + 5;

        // Draw Baskets
        if (entity.type === 'basket') {
            const contents = entity.contents;
            // Determine base image
            let imageKey = 'empty-basket'; // Default to empty

            if (contents.bananas > 0 && contents.apples > 0) {
                if (contents.bananas === 1 && contents.apples === 1) {
                    imageKey = 'one-apple-one-banana-basket';
                } else if (contents.bananas === 2 && contents.apples === 1) {
                    imageKey = 'two-banana-one-apple-basket';
                } else if (contents.apples === 2 && contents.bananas === 1) {
                    imageKey = 'two-apple-one-banana-basket';
                }
            } else if (contents.bananas > 0) {
                imageKey = contents.bananas === 1 ? 'one-banana-basket' : 'two-banana-basket';
            } else if (contents.apples > 0) {
                imageKey = contents.apples === 1 ? 'one-apple-basket' :
                    (contents.apples === 2 ? 'two-apple-basket' : 'three-apple-basket');
            }

            // Draw base basket
            const image = this.images.get(imageKey);
            if (image && image.complete) {
                const imgSize = Math.min(cellSize - 5, laneHeight - 10);
                const imgX = Math.round(x + (cellSize - imgSize) / 2);
                const imgY = Math.round(y + (laneHeight - 30 - imgSize) / 2);

                this.ctx.drawImage(image, imgX, imgY, imgSize, imgSize);
            }
        }
        else if (entity.type === 'farmer') {
            const image = this.images.get('farmer');
            if (image && image.complete) {
                const imgSize = Math.min(cellSize - 10, laneHeight - 30);
                const imgX = Math.round(x + (cellSize - imgSize) / 2);
                const imgY = Math.round(y + (laneHeight - 30 - imgSize) / 2);
                this.ctx.drawImage(image, imgX, imgY, imgSize, imgSize);
            }
        }
    }

    renderFrame(scene, frameIndex = 0) {
        this.drawLane();
        if (!scene || !scene.frames || frameIndex >= scene.frames.length) return;

        const frame = scene.frames[frameIndex];

        // Draw entities: baskets first, then farmer
        const entitiesToDraw = [
            ...frame.entities.filter(e => e.type === 'basket'),
            ...frame.entities.filter(e => e.type === 'farmer')
        ];
        entitiesToDraw.forEach(entity => this.drawEntity(entity));

        if (frame.action) {
            this.drawActionIndicator(frame.action);
        }

        if (frame.highlightPositions) {
            frame.highlightPositions.forEach(pos => this.drawTileHighlight(pos));
        } else if (frame.highlightPos !== undefined) {
            this.drawTileHighlight(frame.highlightPos);
        } else if (frame.highlightWizard) {
            // Fallback if needed, though generator now sends highlightPos
            const wizard = frame.entities.find(e => e.type === 'wizard');
            if (wizard) {
                this.drawTileHighlight(wizard.position);
            }
        }

        const wizard = frame.entities.find(e => e.type === 'wizard');
        if (wizard) {
            this.drawWizard(wizard);
        }

        if (frame.thoughtBubbles && frame.thoughtBubbles.wizard) {
            const wizard = frame.entities.find(e => e.type === 'wizard');
            if (wizard) {
                this.drawWizardThoughtBubbles(wizard.position, frame.thoughtBubbles.wizard);
            }
        }

        this.drawDescriptiveText(frame.description);
    }

    drawWizard(wizard) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const imageKey = wizard.withWand ? 'wizard-wand' : 'wizard';
        const image = this.images.get(imageKey);

        if (image) {
            const wizardSize = Math.round(90 * scaleFactor);
            const x = Math.round(this.laneX + wizard.position * cellSize + (cellSize - wizardSize) / 2);
            const laneY = verticalBorder + Math.round(40 * scaleFactor);
            const y = Math.round(laneY + laneHeight + 160 * scaleFactor);

            this.ctx.drawImage(image, x, y, wizardSize, wizardSize);
        }
    }

    drawTileHighlight(position) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const x = this.laneX + position * cellSize;
        const laneY = verticalBorder + Math.round(40 * scaleFactor);

        this.ctx.strokeStyle = '#d8d8d8ff';
        this.ctx.lineWidth = 6 * scaleFactor;

        const cellHeight = laneHeight - 20;

        this.ctx.strokeRect(x, laneY, cellSize, cellHeight);
    }

    drawWizardThoughtBubbles(wizardPosition, bubbles) {
        const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
        const wizardX = this.laneX + wizardPosition * cellSize + cellSize / 2;
        const laneY = verticalBorder + Math.round(40 * scaleFactor);
        const wizardY = laneY + laneHeight + 120 * scaleFactor;

        // Draw left
        if (bubbles.left) {
            this.drawSingleWizardThoughtBubble(wizardX - 90 * scaleFactor, wizardY + 10 * scaleFactor, bubbles.left, 'left');
        }
        // Draw middle
        if (bubbles.middle) {
            this.drawSingleWizardThoughtBubble(wizardX, wizardY - 25 * scaleFactor, bubbles.middle, 'middle');
        }
        // Draw right
        if (bubbles.right) {
            this.drawSingleWizardThoughtBubble(wizardX + 90 * scaleFactor, wizardY + 10 * scaleFactor, bubbles.right, 'right');
        }
    }

    drawSingleWizardThoughtBubble(x, y, bubbleContent, type) {
        const { scaleFactor } = this.config;
        let thoughtImage;
        let flip = false;

        if (type === 'middle') {
            thoughtImage = this.images.get('thought-middle');
        } else {
            thoughtImage = this.images.get('thought');
            if (type === 'left') flip = true;
        }

        if (!thoughtImage) return;

        this.ctx.save();

        if (flip) {
            this.ctx.scale(-1, 1);
            x = -x;
        }

        const bubbleWidth = type === 'middle' ? 105 * scaleFactor : 130 * scaleFactor;
        const bubbleHeight = type === 'middle' ? 95 * scaleFactor : 80 * scaleFactor;

        // Skip drawing bubble background if noBubble is true
        if (!bubbleContent.noBubble) {
            this.ctx.drawImage(thoughtImage, x - bubbleWidth / 2, y - bubbleHeight / 2, bubbleWidth, bubbleHeight);
        }

        // Draw content
        if (bubbleContent.action) {
            this.ctx.restore(); // Restore from flip
            this.ctx.save();    // Save for safety

            const contentX = flip ? -x : x;
            this.drawWizardBubbleContent(contentX, y, bubbleContent.action, scaleFactor);

            this.ctx.restore();
        } else {
            this.ctx.restore();
        }
    }

    drawWizardBubbleContent(x, y, action, scaleFactor) {
        if (action === 'add_apple_left' || action === 'add_apple_right') {
            const sideText = action === 'add_apple_left' ? 'L' : 'R';
            const img = this.images.get('add-apple');

            if (img) {
                this.ctx.font = `${Math.round(28 * scaleFactor)}px Arial`;
                this.ctx.fillStyle = 'black';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';

                const plusMetrics = this.ctx.measureText('+');
                const sideMetrics = this.ctx.measureText(sideText);

                const gap = 5 * scaleFactor;
                const imgSize = 40 * scaleFactor;

                // Calculate correct aspect ratio for image
                const ratio = img.width / img.height;
                let width = imgSize;
                let height = imgSize;
                if (ratio > 1) height = width / ratio;
                else width = height * ratio;

                const totalWidth = plusMetrics.width + gap + width + gap + sideMetrics.width;

                let xOffset = 0;
                if (action === 'add_apple_left') {
                    xOffset = -10 * scaleFactor;
                } else if (action === 'add_apple_right') {
                    xOffset = 10 * scaleFactor;
                }

                const startX = (x + xOffset) - totalWidth / 2;

                // Draw +
                this.ctx.fillText('+', startX + plusMetrics.width / 2, y);

                // Draw Image
                const imgX = startX + plusMetrics.width + gap;
                this.ctx.drawImage(img, imgX, y - height / 2, width, height);

                // Draw L/R
                const textX = imgX + width + gap + sideMetrics.width / 2;
                this.ctx.fillText(sideText, textX, y);
            }
        }
        // do_nothing is empty
    }

    drawActionIndicator(action) {
        if (action.type === 'wizard_action' && action.subType === 'add_apple') {
            const lightning = this.images.get('lightning');
            if (lightning) {
                const { cellSize, laneHeight, verticalBorder, scaleFactor } = this.config;
                const x = this.laneX + action.targetPosition * cellSize + cellSize / 2;
                const laneY = verticalBorder + Math.round(40 * scaleFactor);
                const y = laneY - Math.round(50 * scaleFactor);
                const size = 60 * scaleFactor;

                this.ctx.save();
                this.ctx.translate(x, y);
                this.ctx.rotate(Math.PI);
                this.ctx.drawImage(lightning, -size / 2, -size / 2, size, size);
                this.ctx.restore();
            }
        }
    }

    drawDescriptiveText(text) {
        if (!text) return;
        const { laneHeight, verticalBorder, scaleFactor } = this.config;
        const textY = verticalBorder + laneHeight + 325 * scaleFactor;
        const textX = this.displayWidth / 2;
        const fontSize = Math.round(14 + 2 * scaleFactor);
        const lineHeight = fontSize * 1.2;

        // Split text into lines
        const lines = text.split('\n');

        this.ctx.fillStyle = '#ffffff';
        // Clear a larger area based on number of lines
        const totalHeight = lines.length * lineHeight;
        this.ctx.fillRect(0, textY - 15, this.displayWidth, totalHeight + 20);

        this.ctx.fillStyle = '#666666';
        this.ctx.font = `italic ${fontSize}px Arial, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        lines.forEach((line, index) => {
            this.ctx.fillText(line, textX, textY + (index * lineHeight));
        });
    }

    playAnimation(scene, options = {}) {
        if (this.isAnimating) this.stopAnimation();

        this.isAnimating = true;
        let frameIndex = 0;
        let lastFrameTime = 0;
        let loopCount = 0;
        const { loop = false, loopDelay = 0, onFrameChange = null, onComplete = null, speed = this.config.animationSpeed } = options;

        const animate = (timestamp) => {
            if (!this.isAnimating) return;

            const currentFrame = scene.frames[frameIndex];
            const currentDuration = (currentFrame && currentFrame.duration) ? currentFrame.duration : speed;

            if (timestamp - lastFrameTime >= currentDuration) {
                lastFrameTime = timestamp;

                this.renderFrame(scene, frameIndex);
                if (onFrameChange) onFrameChange(frameIndex);

                frameIndex++;

                // If we just rendered the first frame of a re-loop, add the delay now
                // so that Frame 0 stays on screen longer.
                if (loop && frameIndex === 1 && loopCount > 0 && loopDelay > 0) {
                    lastFrameTime += loopDelay;
                }

                if (frameIndex >= scene.frames.length) {
                    if (loop) {
                        frameIndex = 0;
                        loopCount++;
                    } else {
                        this.isAnimating = false;
                        if (onComplete) onComplete();
                        return;
                    }
                }
            }
            this.animationFrame = requestAnimationFrame(animate);
        };

        this.animationFrame = requestAnimationFrame(animate);
    }

    stopAnimation() {
        this.isAnimating = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }
}
