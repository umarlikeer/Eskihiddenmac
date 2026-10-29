package uz.uzbek.powerga

import android.app.Activity
import android.os.Bundle
import android.graphics.Typeface
import android.graphics.Color
import android.content.Intent
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var output: TextView
    private lateinit var status: TextView
    private lateinit var populationInput: EditText
    private lateinit var generationsInput: EditText
    private lateinit var runButtons: List<Button>
    private var lastResultText = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        val dataFile = File(filesDir, "DATA_Q14.txt")
        if (!dataFile.exists()) assets.open("DATA_Q14.txt").use { input -> dataFile.outputStream().use { input.copyTo(it) } }
        buildUi()
        status.text = "Офлайн режим тайёр. Тармоқ: DATA_Q14.txt"
    }

    private fun buildUi() {
        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(24))
            setBackgroundColor(Color.rgb(246, 248, 251))
        }
        scroll.addView(root)

        val title = TextView(this).apply {
            text = "ЭЛЕКТР ТАРМОҒИНИ\nГЕНЕТИК АЛГОРИТМ БИЛАН\nОПТИМАЛЛАШТИРИШ"
            textSize = 22f; setTextColor(Color.rgb(20, 54, 90)); typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER; setPadding(0, dp(6), 0, dp(8))
        }
        root.addView(title, matchWrap())
        val subtitle = TextView(this).apply {
            text = "13 та тугун • 20 та шохобча • офлайн ҳисоблаш"
            textSize = 14f; gravity = Gravity.CENTER; setTextColor(Color.DKGRAY)
            setPadding(0, 0, 0, dp(16))
        }
        root.addView(subtitle, matchWrap())

        val section = label("Ҳисоблаш параметрлари")
        root.addView(section, matchWrap())
        val fields = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        populationInput = numberInput("30")
        generationsInput = numberInput("30")
        fields.addView(fieldColumn("Популяция", populationInput), LinearLayout.LayoutParams(0, -2, 1f).apply { rightMargin = dp(6) })
        fields.addView(fieldColumn("Авлодлар", generationsInput), LinearLayout.LayoutParams(0, -2, 1f).apply { leftMargin = dp(6) })
        root.addView(fields, matchWrap())

        root.addView(label("Ҳисоблаш режимини танланг"), matchWrap())
        val baseline = makeButton("0. Бошланғич режим", false)
        val q = makeButton("1. Реактив қувватни оптималлаштириш", false)
        val taps = makeButton("2. Трансформаторни оптималлаштириш", false)
        val combined = makeButton("3. Биргаликда оптималлаштириш", true)
        runButtons = listOf(baseline, q, taps, combined)
        baseline.setOnClickListener { runMode("baseline", baseline) }
        q.setOnClickListener { runMode("q", q) }
        taps.setOnClickListener { runMode("taps", taps) }
        combined.setOnClickListener { runMode("combined", combined) }
        runButtons.forEach { root.addView(it, matchWrap().apply { bottomMargin = dp(8) }) }

        status = TextView(this).apply {
            textSize = 13f; setTextColor(Color.rgb(35, 95, 65)); setPadding(dp(10), dp(10), dp(10), dp(10))
            setBackgroundColor(Color.rgb(226, 242, 233))
        }
        root.addView(status, matchWrap().apply { topMargin = dp(6); bottomMargin = dp(10) })

        root.addView(label("Ҳисоблаш натижаси"), matchWrap())
        output = TextView(this).apply {
            text = "Ҳисоблаш режимини танланг.\n\nЭслатма: оптимал натижаларни диссертацияда ишлатишдан олдин асл Pascal модели билан солиштириш керак."
            textSize = 14f; setTextColor(Color.rgb(35, 43, 54)); setPadding(dp(12), dp(12), dp(12), dp(12))
            setBackgroundColor(Color.WHITE)
        }
        root.addView(output, matchWrap())
        val share = makeButton("Натижани улашиш", false)
        share.setOnClickListener {
            if (lastResultText.isNotBlank()) {
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"; putExtra(Intent.EXTRA_SUBJECT, "Электр тармоғи ҳисоблаш натижаси")
                    putExtra(Intent.EXTRA_TEXT, lastResultText)
                }
                startActivity(Intent.createChooser(intent, "Натижани улашиш"))
            }
        }
        root.addView(share, matchWrap().apply { topMargin = dp(10) })
        setContentView(scroll)
    }

    private fun runMode(mode: String, clicked: Button) {
        val pop = populationInput.text.toString().toIntOrNull() ?: 30
        val gen = generationsInput.text.toString().toIntOrNull() ?: 30
        if (mode != "baseline" && (pop < 10 || gen < 1)) {
            Toast.makeText(this, "Популяция камида 10, авлодлар камида 1 бўлсин", Toast.LENGTH_LONG).show()
            return
        }
        runButtons.forEach { it.isEnabled = false }
        status.text = "Ҳисобланмоқда… Телефонни ёпманг."
        output.text = "Генетик алгоритм ишлаяпти. Бу бир неча сония ёки кўпроқ вақт олиши мумкин."
        val dataPath = File(filesDir, "DATA_Q14.txt").absolutePath
        executor.execute {
            val jsonText = try {
                val module = Python.getInstance().getModule("mobile_api")
                module.callAttr("run_optimization", dataPath, mode, pop, gen).toString()
            } catch (e: Exception) {
                JSONObject().put("ok", false).put("error", e.message ?: "Номаълум хато").toString()
            }
            runOnUiThread {
                runButtons.forEach { it.isEnabled = true }
                try {
                    val json = JSONObject(jsonText)
                    if (!json.optBoolean("ok", false)) {
                        val error = json.optString("error", "Ҳисоблаш хатоси")
                        status.text = "Хато юз берди"
                        output.text = "ХАТО:\n$error\n\nАгар муаммо давом этса, тармоқ маълумотларини текширинг."
                        lastResultText = output.text.toString()
                    } else {
                        val text = formatResult(json)
                        output.text = text
                        lastResultText = text
                        status.text = "Ҳисоблаш муваффақиятли тугади"
                    }
                } catch (e: Exception) {
                    status.text = "Натижани ўқишда хато"
                    output.text = jsonText
                    lastResultText = jsonText
                }
            }
        }
    }

    private fun formatResult(j: JSONObject): String {
        val mode = when (j.optString("mode")) {
            "baseline" -> "Бошланғич режим"
            "q" -> "Реактив қувват оптималлаштирилди"
            "taps" -> "Трансформатор коэффициентлари оптималлаштирилди"
            else -> "Биргаликда оптималлаштириш"
        }
        val initial = j.optDouble("initial_losses")
        val final = j.optDouble("final_losses")
        val reduction = j.optDouble("reduction_mw")
        val percent = j.optDouble("reduction_percent")
        val sb = StringBuilder()
        sb.append("РЕЖИМ: ").append(mode).append("\n\n")
        sb.append(String.format(Locale.US, "Бошланғич актив исроф: %.6f МВт\n", initial))
        sb.append(String.format(Locale.US, "Якуний актив исроф: %.6f МВт\n", final))
        sb.append(String.format(Locale.US, "Исроф камайиши: %.6f МВт (%.3f%%)\n", reduction, percent))
        sb.append("Авлодлар сони: ").append(j.optInt("generations_run")).append("\n")
        sb.append("\nКУЧЛАНИШЛАР (p.u.)\n")
        val volts = j.optJSONArray("final_voltages")
        if (volts != null) for (i in 0 until volts.length()) {
            val v = volts.getJSONObject(i)
            sb.append(String.format(Locale.US, "Тугун %d: %.5f p.u. (%.2f кВ)\n", v.getInt("bus"), v.optDouble("pu"), v.optDouble("kv")))
        }
        val q = j.optJSONObject("q_values")
        if (q != null && q.length() > 0) {
            sb.append("\nОПТИМАЛ РЕАКТИВ ҚУВВАТ (MVAr)\n")
            val keys = q.keys()
            while (keys.hasNext()) { val key = keys.next(); sb.append(String.format(Locale.US, "Тугун %s: %.5f\n", key, q.optDouble(key))) }
        }
        val taps = j.optJSONObject("taps")
        if (taps != null && taps.length() > 0) {
            sb.append("\nТРАНСФОРМАТОР КОЭФФИЦИЕНТЛАРИ\n")
            val keys = taps.keys()
            while (keys.hasNext()) {
                val key = keys.next(); val t = taps.getJSONObject(key)
                sb.append(String.format(Locale.US, "%d-%d: Kre=%.5f, Kim=%.5f\n", t.getInt("from"), t.getInt("to"), t.optDouble("kre"), t.optDouble("kim")))
            }
        }
        val violations = j.optJSONArray("violations")
        sb.append("\nКучланиш чеклови бузилиши: ").append(if (violations == null) 0 else violations.length()).append(" та\n")
        sb.append("\nМуҳим: натижа ҳисоблаш моделига боғлиқ. Илмий ишда қўллашдан олдин асл Pascal дастури билан таққосланг.")
        return sb.toString()
    }

    private fun label(text: String) = TextView(this).apply {
        this.text = text; textSize = 16f; typeface = Typeface.DEFAULT_BOLD
        setTextColor(Color.rgb(20, 54, 90)); setPadding(0, dp(12), 0, dp(8))
    }

    private fun numberInput(value: String) = EditText(this).apply {
        setText(value); textSize = 16f; inputType = android.text.InputType.TYPE_CLASS_NUMBER
        setSingleLine(true); setPadding(dp(12), dp(8), dp(12), dp(8)); setBackgroundColor(Color.WHITE)
    }

    private fun fieldColumn(caption: String, input: EditText): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(TextView(this@MainActivity).apply { text = caption; textSize = 13f; setTextColor(Color.DKGRAY) }, matchWrap())
        addView(input, matchWrap().apply { topMargin = dp(4) })
    }

    private fun makeButton(textValue: String, primary: Boolean): Button = Button(this).apply {
        text = textValue; textSize = 14f; isAllCaps = false
        setTextColor(if (primary) Color.WHITE else Color.rgb(20, 54, 90))
        setBackgroundColor(if (primary) Color.rgb(25, 91, 145) else Color.rgb(224, 234, 243))
        minHeight = dp(48)
    }

    private fun matchWrap() = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    override fun onDestroy() {
        super.onDestroy()
        executor.shutdown()
    }
}
