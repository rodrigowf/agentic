#!/usr/bin/env node
/**
 * Puppeteer script to capture screenshot and console logs from an HTML file.
 *
 * Usage: node puppeteer_capture.js <html_file_path> <screenshot_output_path>
 *
 * Output: JSON object with console_logs field
 *
 * Example:
 *   node puppeteer_capture.js /path/to/file.html /path/to/screenshot.png
 *   -> {"console_logs": "log: Hello\nerror: Something failed"}
 */

// Try to load puppeteer from debug/node_modules (shared with debug tools)
const path = require('path');
const fs = require('fs');
const puppeteerPath = path.join(__dirname, '..', '..', 'debug', 'node_modules', 'puppeteer');
const puppeteer = require(puppeteerPath);

async function captureHtml(htmlPath, screenshotPath) {
    const consoleLogs = [];

    // Validate input file exists
    if (!fs.existsSync(htmlPath)) {
        throw new Error(`HTML file not found: ${htmlPath}`);
    }

    // Ensure output directory exists
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
    }

    // Launch browser
    const browser = await puppeteer.launch({
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    });

    try {
        const page = await browser.newPage();

        // Set viewport
        await page.setViewport({
            width: 1280,
            height: 720,
            deviceScaleFactor: 1
        });

        // Capture console messages
        page.on('console', (msg) => {
            const type = msg.type();
            const text = msg.text();
            consoleLogs.push(`${type}: ${text}`);
        });

        // Capture page errors
        page.on('pageerror', (error) => {
            consoleLogs.push(`error: ${error.message}`);
        });

        // Capture request failures
        page.on('requestfailed', (request) => {
            consoleLogs.push(`request-failed: ${request.url()} - ${request.failure().errorText}`);
        });

        // Navigate to the HTML file
        const fileUrl = `file://${path.resolve(htmlPath)}`;
        await page.goto(fileUrl, {
            waitUntil: 'networkidle0',
            timeout: 20000
        });

        // Wait a bit for any animations or async rendering
        await page.waitForTimeout(500);

        // Take screenshot
        await page.screenshot({
            path: screenshotPath,
            fullPage: false // Capture viewport only
        });

        // Return results
        return {
            success: true,
            console_logs: consoleLogs.join('\n'),
            screenshot_path: screenshotPath
        };

    } finally {
        await browser.close();
    }
}

// Main execution
async function main() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('Usage: node puppeteer_capture.js <html_file_path> <screenshot_output_path>');
        process.exit(1);
    }

    const [htmlPath, screenshotPath] = args;

    try {
        const result = await captureHtml(htmlPath, screenshotPath);
        // Output JSON result to stdout
        console.log(JSON.stringify(result));
        process.exit(0);
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message,
            console_logs: ''
        }));
        process.exit(1);
    }
}

main();
