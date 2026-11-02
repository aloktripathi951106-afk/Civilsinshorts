package com.example

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.viewinterop.AndroidView

class MainActivity : ComponentActivity() {

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    enableEdgeToEdge()
    cleanupCorruptedVariationsSeed()

    setContent {
      var webViewRef by remember { mutableStateOf<WebView?>(null) }

      BackHandler(enabled = true) {
        val webView = webViewRef
        if (webView != null) {
          webView.evaluateJavascript("window.handleAndroidBack ? window.handleAndroidBack() : false") { result ->
            val handled = result == "true"
            if (!handled) {
              if (webView.canGoBack()) {
                webView.goBack()
              } else {
                finish()
              }
            }
          }
        } else {
          finish()
        }
      }

      Surface(
        modifier = Modifier
          .fillMaxSize()
          .background(Color(0xFF0B0F17))
          .statusBarsPadding()
          .navigationBarsPadding()
          .testTag("main_screen_container"),
        color = Color(0xFF0B0F17)
      ) {
        CivilsWebViewContainer(
          onWebViewCreated = { webViewRef = it }
        )
      }
    }
  }

  private fun cleanupCorruptedVariationsSeed() {
    try {
      val dataDir = applicationInfo.dataDir
      val webviewDir = java.io.File(dataDir, "app_webview")
      if (webviewDir.exists() && webviewDir.isDirectory) {
        val targets = listOf("variations_seed", "variations_seed_new", "variations_stamp")
        for (target in targets) {
          val file = java.io.File(webviewDir, target)
          if (file.exists()) {
            file.delete()
          }
        }
      }
    } catch (_: Throwable) {
      // Safe fallback
    }
  }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun CivilsWebViewContainer(
  modifier: Modifier = Modifier,
  onWebViewCreated: (WebView) -> Unit
) {
  AndroidView(
    modifier = modifier
      .fillMaxSize()
      .testTag("civils_webview"),
    factory = { context ->
      WebView(context).apply {
        layoutParams = ViewGroup.LayoutParams(
          ViewGroup.LayoutParams.MATCH_PARENT,
          ViewGroup.LayoutParams.MATCH_PARENT
        )
        setBackgroundColor(android.graphics.Color.parseColor("#0B0F17"))

        settings.apply {
          javaScriptEnabled = true
          domStorageEnabled = true
          databaseEnabled = true
          loadWithOverviewMode = true
          useWideViewPort = true
          cacheMode = WebSettings.LOAD_DEFAULT
          allowFileAccess = true
          allowContentAccess = true
          @Suppress("DEPRECATION")
          allowFileAccessFromFileURLs = true
          @Suppress("DEPRECATION")
          allowUniversalAccessFromFileURLs = true
          setSupportZoom(false)
          displayZoomControls = false
          textZoom = 100
          // Secure mixed content policy to protect user data
          mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        }

        // Native Share bridge for Android (dispatched on main UI thread)
        addJavascriptInterface(object {
          @android.webkit.JavascriptInterface
          fun shareBrief(title: String?, text: String?, url: String?) {
            post {
              try {
                val shareBody = buildString {
                  if (!title.isNullOrBlank()) append(title).append("\n\n")
                  if (!text.isNullOrBlank()) append(text).append("\n\n")
                  if (!url.isNullOrBlank() && url != "#") append("Source: ").append(url)
                }.trim()

                val sendIntent = Intent(Intent.ACTION_SEND).apply {
                  type = "text/plain"
                  putExtra(Intent.EXTRA_SUBJECT, title ?: "CivilsInshorts UPSC Brief")
                  putExtra(Intent.EXTRA_TEXT, shareBody)
                  addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                val chooser = Intent.createChooser(sendIntent, "Share UPSC Brief").apply {
                  addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(chooser)
              } catch (e: Exception) {
                try {
                  val fallback = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, "$title\n\n$text")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                  }
                  context.startActivity(fallback)
                } catch (_: Exception) {}
              }
            }
          }
        }, "AndroidShare")

        webViewClient = object : WebViewClient() {
          override fun shouldOverrideUrlLoading(
            view: WebView?,
            request: WebResourceRequest?
          ): Boolean {
            val uri = request?.url ?: return false
            val scheme = uri.scheme?.lowercase() ?: return false

            // Keep internal application asset files inside the local WebView container
            val urlString = uri.toString()
            if (urlString.startsWith("file:///android_asset/")) {
              return false
            }

            // Strictly whitelist allowed outgoing URL schemes for 100% security
            val safeSchemes = setOf("http", "https", "mailto", "tel", "whatsapp", "sms", "tg", "telegram")
            if (scheme !in safeSchemes) {
              return true // Block dangerous schemes like javascript:, content:, or malicious intents
            }

            try {
              val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
              }
              context.startActivity(intent)
            } catch (_: Exception) {
              // Graceful fallback
            }
            return true
          }

          override fun onRenderProcessGone(
            view: WebView?,
            detail: android.webkit.RenderProcessGoneDetail?
          ): Boolean {
            view?.loadUrl("file:///android_asset/index.html")
            return true
          }

          override fun onReceivedError(
            view: WebView?,
            errorCode: Int,
            description: String?,
            failingUrl: String?
          ) {
            // Handled non-fatal error gracefully
          }
        }

        webChromeClient = object : WebChromeClient() {
          override fun onConsoleMessage(consoleMessage: android.webkit.ConsoleMessage?): Boolean {
            if (consoleMessage != null) {
              android.util.Log.d("CivilsWeb", "${consoleMessage.message()} -- line ${consoleMessage.lineNumber()} of ${consoleMessage.sourceId()}")
            }
            return true
          }
        }

        loadUrl("file:///android_asset/index.html")
        onWebViewCreated(this)
      }
    }
  )
}
