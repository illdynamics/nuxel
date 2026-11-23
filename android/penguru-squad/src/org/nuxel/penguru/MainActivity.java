package org.nuxel.penguru;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Offline-first PenGuru Squad shell.
 *
 * The complete PWA is bundled under assets/public and served from a private
 * https://appassets.androidplatform.net origin. No third-party WebView
 * dependency is used: shouldInterceptRequest reads only files inside the APK.
 * The only network calls are the owner-configured Nuxel bridge and links the
 * owner explicitly opens (Hugging Face provenance links).
 */
public class MainActivity extends Activity {
    private static final String TAG = "PenGuruSquad";
    private static final String ASSET_HOST = "appassets.androidplatform.net";
    private static final String START_PATH = "/pwa/nuxel-apps/penguru/index.html";
    private static final int MIC_REQUEST = 7001;

    private WebView webView;
    private PermissionRequest pendingAudio;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#101b2c"));
        getWindow().setNavigationBarColor(Color.parseColor("#0b1422"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0b1422"));
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setLoadWithOverviewMode(false);
        settings.setUseWideViewPort(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            // The owner-configured bridge is usually plain http on loopback or
            // a private LAN. TLS cannot be assumed for a local-only service.
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(
                    (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0);
        }

        webView.setWebViewClient(new LocalAssetClient());
        webView.setWebChromeClient(new PenGuruChromeClient());
        webView.addJavascriptInterface(new AndroidBridge(), "NuxelAndroid");
        applySystemBarInsets(webView);
        setContentView(webView);

        if (savedInstanceState == null) {
            webView.loadUrl("https://" + ASSET_HOST + START_PATH);
        } else {
            webView.restoreState(savedInstanceState);
        }
    }


    /** Keep the WebView content out of status/navigation bars on Android 15+
     *  edge-to-edge and on cutout displays. */
    private static void applySystemBarInsets(final WebView view) {
        view.setOnApplyWindowInsetsListener((v, insets) -> {
            int top = 0, bottom = 0, left = 0, right = 0;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                android.graphics.Insets bars = insets.getInsets(
                        android.view.WindowInsets.Type.systemBars()
                                | android.view.WindowInsets.Type.displayCutout());
                top = bars.top;
                bottom = bars.bottom;
                left = bars.left;
                right = bars.right;
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                top = insets.getSystemWindowInsetTop();
                bottom = insets.getSystemWindowInsetBottom();
                left = insets.getSystemWindowInsetLeft();
                right = insets.getSystemWindowInsetRight();
            }
            v.setPadding(left, top, right, bottom);
            return insets;
        });
        view.requestApplyInsets();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        if (webView != null) {
            webView.saveState(outState);
        }
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode != MIC_REQUEST || pendingAudio == null) {
            return;
        }
        boolean granted = results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED;
        if (granted) {
            pendingAudio.grant(pendingAudio.getResources());
        } else {
            pendingAudio.deny();
        }
        pendingAudio = null;
    }

    /**
     * Narrow JS bridge for the two browser actions a WebView cannot complete
     * on its own: saving an exported response and opening a provenance link in
     * the owner's browser.  It is exposed only to the bundled app origin; the
     * WebView never navigates to remote HTML.
     */
    private final class AndroidBridge {
        @JavascriptInterface
        public String saveText(String filename, String text) {
            if (text == null) {
                return null;
            }
            try {
                String safe = sanitizeFilename(filename);
                if (safe.isEmpty()) {
                    safe = "penguru-response.txt";
                }
                if (!safe.contains(".")) {
                    safe += ".txt";
                }
                byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.MediaColumns.DISPLAY_NAME, safe);
                    values.put(MediaStore.MediaColumns.MIME_TYPE, "text/plain");
                    values.put(MediaStore.MediaColumns.RELATIVE_PATH,
                            Environment.DIRECTORY_DOWNLOADS + "/PenGuru");
                    values.put(MediaStore.MediaColumns.IS_PENDING, 1);
                    Uri uri = getContentResolver().insert(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) {
                        return null;
                    }
                    try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                        if (out == null) {
                            getContentResolver().delete(uri, null, null);
                            return null;
                        }
                        out.write(bytes);
                    } catch (IOException error) {
                        getContentResolver().delete(uri, null, null);
                        return null;
                    }
                    values.clear();
                    values.put(MediaStore.MediaColumns.IS_PENDING, 0);
                    try {
                        getContentResolver().update(uri, values, null, null);
                    } catch (RuntimeException error) {
                        // A pending row that cannot be published is not a
                        // saved export; remove it rather than leave an
                        // invisible orphan in Downloads.
                        getContentResolver().delete(uri, null, null);
                        return null;
                    }
                    // MediaStore may de-duplicate an existing name (for
                    // example "file (1).txt").  Report the name the owner
                    // will actually see, not the requested one.
                    return "Downloads/PenGuru/" + mediaDisplayName(uri, safe);
                }
                File base = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (base == null) {
                    return null;
                }
                File dir = new File(base, "PenGuru");
                if (!dir.exists() && !dir.mkdirs()) {
                    return null;
                }
                File target = new File(dir, safe);
                try (FileOutputStream out = new FileOutputStream(target)) {
                    out.write(bytes);
                } catch (IOException error) {
                    return null;
                }
                return target.getAbsolutePath();
            } catch (RuntimeException error) {
                // Fail closed: never crash the WebView bridge on a storage or
                // permission refusal; the page reports that nothing was saved.
                return null;
            }
        }

        @JavascriptInterface
        public boolean openExternal(String url) {
            if (url == null) {
                return false;
            }
            Uri uri = Uri.parse(url);
            String scheme = uri.getScheme();
            if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
                return false;
            }
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
                return true;
            } catch (RuntimeException unavailable) {
                return false;
            }
        }

        private String mediaDisplayName(Uri uri, String fallback) {
            try (Cursor cursor = getContentResolver().query(
                    uri, new String[]{MediaStore.MediaColumns.DISPLAY_NAME},
                    null, null, null)) {
                if (cursor != null && cursor.moveToFirst()) {
                    String name = cursor.getString(0);
                    if (name != null && !name.isEmpty()) {
                        return name;
                    }
                }
            } catch (RuntimeException ignored) {
                // The export succeeded; fall back to the requested name.
            }
            return fallback;
        }

        private String sanitizeFilename(String filename) {
            if (filename == null) {
                return "";
            }
            String safe = filename.replaceAll("[^A-Za-z0-9._-]", "_");
            while (safe.startsWith(".")) {
                safe = safe.substring(1);
            }
            return safe.length() > 80 ? safe.substring(0, 80) : safe;
        }
    }

    private final class PenGuruChromeClient extends WebChromeClient {
        @Override
        public void onPermissionRequest(final PermissionRequest request) {
            boolean wantsAudio = false;
            for (String resource : request.getResources()) {
                if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                    wantsAudio = true;
                }
            }
            if (!wantsAudio || request.getOrigin() == null
                    || !ASSET_HOST.equals(request.getOrigin().getHost())) {
                request.deny();
                return;
            }
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED) {
                request.grant(request.getResources());
                return;
            }
            if (pendingAudio != null) {
                pendingAudio.deny();
            }
            pendingAudio = request;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_REQUEST);
        }

        @Override
        public boolean onConsoleMessage(ConsoleMessage message) {
            if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
                Log.d(TAG, message.message() + " @" + message.lineNumber());
            }
            return true;
        }
    }

    private final class LocalAssetClient extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri == null || !ASSET_HOST.equals(uri.getHost())) {
                return null;
            }
            String path = uri.getPath();
            if (path == null || path.isEmpty() || "/".equals(path)) {
                path = START_PATH;
            }
            while (path.startsWith("/")) {
                path = path.substring(1);
            }
            if (path.isEmpty() || path.contains("..") || path.contains("\\")) {
                return notFound();
            }
            try {
                InputStream stream = getAssets().open("public/" + path);
                WebResourceResponse response = new WebResourceResponse(
                        mimeFor(path), "UTF-8", stream);
                Map<String, String> headers = new HashMap<>();
                headers.put("Cache-Control", "no-store");
                headers.put("X-Content-Type-Options", "nosniff");
                response.setResponseHeaders(headers);
                return response;
            } catch (IOException missing) {
                return notFound();
            }
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri == null) {
                return false;
            }
            if (ASSET_HOST.equals(uri.getHost())) {
                return false;
            }
            String scheme = uri.getScheme();
            if ("http".equals(scheme) || "https".equals(scheme)) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (RuntimeException ignored) {
                    // No browser installed; keep the app responsive.
                }
                return true;
            }
            return false;
        }

        private WebResourceResponse notFound() {
            Map<String, String> headers = new HashMap<>();
            headers.put("Cache-Control", "no-store");
            return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
                    headers, new ByteArrayInputStream(
                            "Not found".getBytes(StandardCharsets.UTF_8)));
        }
    }

    private static String mimeFor(String path) {
        String extension = MimeTypeMap.getFileExtensionFromUrl(path);
        if (extension != null && !extension.isEmpty()) {
            String mime = MimeTypeMap.getSingleton()
                    .getMimeTypeFromExtension(extension.toLowerCase());
            if (mime != null) {
                return mime;
            }
        }
        if (path.endsWith(".js") || path.endsWith(".mjs")) return "text/javascript";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".json") || path.endsWith(".webmanifest")) return "application/json";
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".svg")) return "image/svg+xml";
        return "application/octet-stream";
    }
}
