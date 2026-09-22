package com.suriaraj.sandminertrainer;

import static android.content.pm.PackageManager.PERMISSION_GRANTED;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.IBinder;
import android.os.RemoteException;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import rikka.shizuku.Shizuku;

public class MainActivity extends Activity {

    private static final int SHIZUKU_PERMISSION_REQUEST = 1001;
    private static final String GAME_PACKAGE = "com.hcph.sandexplore";
    private static final String SUPPORTED_GAME_VERSION = "3.6.1";

    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private TextView accessStatus;
    private TextView gameStatus;
    private TextView currentMoney;
    private TextView currentGems;

    private EditText moneyInput;
    private EditText gemsInput;

    private Button connectButton;
    private Button refreshButton;
    private Button applyButton;
    private Button restoreButton;
    private Button launchButton;
    private Button shizukuButton;

    private ISaveService saveService;
    private boolean shizukuBound;

    private final Shizuku.OnBinderReceivedListener binderReceivedListener =
            this::onShizukuBinderReady;

    private final Shizuku.OnBinderDeadListener binderDeadListener = () ->
            runOnUiThread(() -> {
                saveService = null;
                shizukuBound = false;
                accessStatus.setText("Shizuku: not running");
                updateButtons();
            });

    private final Shizuku.OnRequestPermissionResultListener
            permissionResultListener = (requestCode, grantResult) -> {
        if (requestCode != SHIZUKU_PERMISSION_REQUEST) {
            return;
        }

        if (grantResult == PERMISSION_GRANTED) {
            bindSaveService();
        } else {
            runOnUiThread(() -> {
                accessStatus.setText("Shizuku permission was not granted.");
                updateButtons();
            });
        }
    };

    private final ServiceConnection serviceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder binder) {
            saveService = ISaveService.Stub.asInterface(binder);
            shizukuBound = saveService != null;
            runOnUiThread(() -> {
                accessStatus.setText(
                        shizukuBound
                                ? "Shizuku: connected ✓"
                                : "Shizuku: user service unavailable");
                updateButtons();
                if (shizukuBound) {
                    refreshValues();
                }
            });
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            saveService = null;
            shizukuBound = false;
            runOnUiThread(() -> {
                accessStatus.setText("Shizuku: service disconnected");
                updateButtons();
            });
        }
    };

    private final Shizuku.UserServiceArgs userServiceArgs =
            new Shizuku.UserServiceArgs(
                    new ComponentName(
                            BuildConfig.APPLICATION_ID,
                            SaveUserService.class.getName()))
                    .daemon(false)
                    .processNameSuffix("save")
                    .debuggable(BuildConfig.DEBUG)
                    .version(BuildConfig.VERSION_CODE);

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        checkGameVersion();

        Shizuku.addBinderReceivedListenerSticky(binderReceivedListener);
        Shizuku.addBinderDeadListener(binderDeadListener);
        Shizuku.addRequestPermissionResultListener(permissionResultListener);
    }

    @Override
    protected void onDestroy() {
        Shizuku.removeBinderReceivedListener(binderReceivedListener);
        Shizuku.removeBinderDeadListener(binderDeadListener);
        Shizuku.removeRequestPermissionResultListener(permissionResultListener);

        if (shizukuBound) {
            try {
                Shizuku.unbindUserService(
                        userServiceArgs, serviceConnection, false);
            } catch (Throwable ignored) {
            }
        }

        io.shutdownNow();
        super.onDestroy();
    }

    private void onShizukuBinderReady() {
        runOnUiThread(() -> {
            accessStatus.setText("Shizuku: available");
            updateButtons();
        });
        ensurePermissionAndBind();
    }

    private void ensurePermissionAndBind() {
        try {
            if (Shizuku.isPreV11()) {
                runOnUiThread(() ->
                        accessStatus.setText("Shizuku API 11+ is required."));
                return;
            }

            if (Shizuku.checkSelfPermission() == PERMISSION_GRANTED) {
                bindSaveService();
                return;
            }

            if (Shizuku.shouldShowRequestPermissionRationale()) {
                runOnUiThread(() ->
                        accessStatus.setText(
                                "Grant Sandminer Trainer access in Shizuku."));
                return;
            }

            Shizuku.requestPermission(SHIZUKU_PERMISSION_REQUEST);
        } catch (Throwable t) {
            runOnUiThread(() -> {
                accessStatus.setText(
                        "Shizuku is not installed or not running.");
                updateButtons();
            });
        }
    }

    private void bindSaveService() {
        try {
            if (shizukuBound) {
                return;
            }
            accessStatus.setText("Shizuku: connecting…");
            Shizuku.bindUserService(userServiceArgs, serviceConnection);
        } catch (Throwable t) {
            accessStatus.setText("Shizuku connection failed: " + safeMessage(t));
            updateButtons();
        }
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(22), dp(20), dp(28));
        scroll.addView(root);

        TextView title = text("Sandminer Trainer", 28, true);
        root.addView(title);

        TextView subtitle = text(
                "Money + Gems editor • Sand Miner 3.6.1", 14, false);
        subtitle.setTextColor(Color.DKGRAY);
        root.addView(subtitle);

        Space spacer = new Space(this);
        root.addView(spacer,
                new LinearLayout.LayoutParams(1, dp(14)));

        accessStatus = card(
                "Shizuku: checking…",
                Color.rgb(255, 244, 214));
        root.addView(accessStatus);

        gameStatus = text("Sand Miner: checking…", 14, false);
        root.addView(gameStatus);

        currentMoney = text("Money: —", 24, true);
        currentGems = text("Gems: —", 24, true);
        root.addView(currentMoney);
        root.addView(currentGems);

        moneyInput = numberInput("New money");
        gemsInput = numberInput("New gems");

        root.addView(moneyInput);
        root.addView(gemsInput);

        connectButton = button("Connect / request Shizuku access");
        refreshButton = button("Refresh values");
        applyButton = button("Apply safely");
        restoreButton = button("Restore last trainer backup");
        launchButton = button("Launch Sand Miner");
        shizukuButton = button("Open / install Shizuku");

        root.addView(connectButton);
        root.addView(refreshButton);
        root.addView(applyButton);
        root.addView(restoreButton);
        root.addView(launchButton);
        root.addView(shizukuButton);

        TextView safety = card(
                "LEVEL PROGRESS PROTECTION\n\n"
                        + "This trainer edits save.dat only. "
                        + "The level save is not opened or modified. "
                        + "A timestamped copy of save.dat is created before "
                        + "every edit and every write is verified.",
                Color.rgb(232, 248, 236));
        safety.setTextSize(14);
        root.addView(safety);

        TextView help = text(
                "Non-root setup: start Shizuku using Wireless debugging, "
                        + "then return here and grant access. "
                        + "After a phone reboot Shizuku normally needs "
                        + "to be started again.",
                13,
                false);
        help.setPadding(0, dp(14), 0, 0);
        root.addView(help);

        connectButton.setOnClickListener(v -> ensurePermissionAndBind());
        refreshButton.setOnClickListener(v -> refreshValues());
        applyButton.setOnClickListener(v -> applyValues());
        restoreButton.setOnClickListener(v -> restoreLatest());
        launchButton.setOnClickListener(v -> launchGame());
        shizukuButton.setOnClickListener(v -> openShizuku());

        setContentView(scroll);
        updateButtons();
    }

    private void checkGameVersion() {
        try {
            PackageInfo info = getPackageManager()
                    .getPackageInfo(GAME_PACKAGE, 0);

            String version = info.versionName == null ? "unknown" : info.versionName;
            if (SUPPORTED_GAME_VERSION.equals(version)) {
                gameStatus.setText("Sand Miner " + version + ": supported ✓");
            } else {
                gameStatus.setText(
                        "Sand Miner " + version
                                + ": unsupported — editing disabled");
            }
        } catch (Exception e) {
            gameStatus.setText("Sand Miner is not installed.");
        }
        updateButtons();
    }

    private boolean isSupportedGame() {
        try {
            PackageInfo info = getPackageManager()
                    .getPackageInfo(GAME_PACKAGE, 0);
            return SUPPORTED_GAME_VERSION.equals(info.versionName);
        } catch (Exception e) {
            return false;
        }
    }

    private void refreshValues() {
        ISaveService service = saveService;
        if (service == null) {
            toast("Connect Shizuku first.");
            return;
        }

        setBusy(true);

        io.execute(() -> {
            try {
                String result = service.getState();
                handleStateResult(result, true);
            } catch (Throwable t) {
                showOperationError(t);
            }
        });
    }

    private void applyValues() {
        if (!isSupportedGame()) {
            toast("Editing is disabled for this Sand Miner version.");
            return;
        }

        Integer money = parseValue(moneyInput, "money");
        Integer gems = parseValue(gemsInput, "gems");

        if (money == null || gems == null) {
            return;
        }

        ISaveService service = saveService;
        if (service == null) {
            toast("Connect Shizuku first.");
            return;
        }

        setBusy(true);

        io.execute(() -> {
            try {
                String result = service.applyValues(money, gems);

                if (!result.startsWith("OK|")) {
                    throw new IllegalStateException(cleanError(result));
                }

                Map<String, String> values = parseResult(result);

                runOnUiThread(() -> {
                    currentMoney.setText("Money: " + values.get("money"));
                    currentGems.setText("Gems: " + values.get("gems"));
                    moneyInput.setText(values.get("money"));
                    gemsInput.setText(values.get("gems"));
                    toast("Saved and verified. Backup: "
                            + values.get("backup"));
                    setBusy(false);
                });
            } catch (Throwable t) {
                showOperationError(t);
            }
        });
    }

    private void restoreLatest() {
        ISaveService service = saveService;
        if (service == null) {
            toast("Connect Shizuku first.");
            return;
        }

        setBusy(true);

        io.execute(() -> {
            try {
                String result = service.restoreLatest();

                if (!result.startsWith("OK|")) {
                    throw new IllegalStateException(cleanError(result));
                }

                Map<String, String> values = parseResult(result);

                runOnUiThread(() -> {
                    currentMoney.setText("Money: " + values.get("money"));
                    currentGems.setText("Gems: " + values.get("gems"));
                    moneyInput.setText(values.get("money"));
                    gemsInput.setText(values.get("gems"));
                    toast("Restored: " + values.get("restored"));
                    setBusy(false);
                });
            } catch (Throwable t) {
                showOperationError(t);
            }
        });
    }

    private void handleStateResult(String result, boolean updateInputs) {
        if (!result.startsWith("OK|")) {
            showOperationError(
                    new IllegalStateException(cleanError(result)));
            return;
        }

        Map<String, String> values = parseResult(result);

        runOnUiThread(() -> {
            String money = values.get("money");
            String gems = values.get("gems");

            currentMoney.setText("Money: " + money);
            currentGems.setText("Gems: " + gems);

            if (updateInputs) {
                moneyInput.setText(money);
                gemsInput.setText(gems);
            }

            accessStatus.setText("Shizuku: connected ✓");
            setBusy(false);
        });
    }

    private Integer parseValue(EditText input, String label) {
        String value = input.getText().toString().trim();

        if (value.isEmpty()) {
            toast("Enter " + label + ".");
            return null;
        }

        try {
            long parsed = Long.parseLong(value);

            if (parsed < 0 || parsed > Integer.MAX_VALUE) {
                toast(label + " must be 0 to "
                        + Integer.MAX_VALUE + ".");
                return null;
            }

            return (int) parsed;
        } catch (NumberFormatException e) {
            toast("Use whole numbers for " + label + ".");
            return null;
        }
    }

    private void launchGame() {
        Intent intent = getPackageManager()
                .getLaunchIntentForPackage(GAME_PACKAGE);

        if (intent == null) {
            toast("Sand Miner is not installed.");
            return;
        }

        startActivity(intent);
    }

    private void openShizuku() {
        try {
            Intent launch = getPackageManager()
                    .getLaunchIntentForPackage(
                            "moe.shizuku.privileged.api");

            if (launch != null) {
                startActivity(launch);
                return;
            }
        } catch (Throwable ignored) {
        }

        Intent browser = new Intent(
                Intent.ACTION_VIEW,
                Uri.parse("https://shizuku.rikka.app/download/"));
        startActivity(browser);
    }

    private Map<String, String> parseResult(String result) {
        Map<String, String> values = new LinkedHashMap<>();

        String[] parts = result.split("\\|");

        for (int i = 1; i < parts.length; i++) {
            int equals = parts[i].indexOf('=');
            if (equals > 0) {
                values.put(
                        parts[i].substring(0, equals),
                        parts[i].substring(equals + 1));
            }
        }

        return values;
    }

    private String cleanError(String result) {
        if (result != null && result.startsWith("ERR|")) {
            return result.substring(4);
        }
        return result == null ? "Unknown error" : result;
    }

    private void showOperationError(Throwable t) {
        runOnUiThread(() -> {
            toast("No save change made: " + safeMessage(t));
            setBusy(false);
        });
    }

    private String safeMessage(Throwable t) {
        String message = t.getMessage();
        if (message == null || message.trim().isEmpty()) {
            return t.getClass().getSimpleName();
        }
        return message;
    }

    private void setBusy(boolean busy) {
        connectButton.setEnabled(!busy);
        shizukuButton.setEnabled(!busy);
        launchButton.setEnabled(!busy);

        boolean active = !busy && shizukuBound;

        refreshButton.setEnabled(active);
        restoreButton.setEnabled(active);
        applyButton.setEnabled(active && isSupportedGame());
    }

    private void updateButtons() {
        setBusy(false);
    }

    private TextView text(String value, int sp, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(Color.rgb(32, 32, 32));
        view.setPadding(0, dp(5), 0, dp(5));

        if (bold) {
            view.setTypeface(
                    view.getTypeface(),
                    android.graphics.Typeface.BOLD);
        }

        return view;
    }

    private TextView card(String value, int color) {
        TextView view = text(value, 16, true);
        view.setPadding(dp(14), dp(14), dp(14), dp(14));
        view.setBackgroundColor(color);
        return view;
    }

    private EditText numberInput(String hint) {
        EditText input = new EditText(this);
        input.setHint(hint);
        input.setTextSize(18);
        input.setSingleLine(true);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setPadding(dp(10), dp(10), dp(10), dp(10));
        return input;
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);

        LinearLayout.LayoutParams params =
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        dp(52));

        params.setMargins(0, dp(6), 0, dp(6));
        button.setLayoutParams(params);

        return button;
    }

    private int dp(int value) {
        return (int) (
                value * getResources()
                        .getDisplayMetrics().density + 0.5f);
    }

    private void toast(String message) {
        Toast.makeText(
                this, message, Toast.LENGTH_LONG).show();
    }
}
