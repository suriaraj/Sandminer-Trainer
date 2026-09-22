package com.suriaraj.sandminertrainer;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public final class SaveUserService extends ISaveService.Stub {

    private static final String GAME_PACKAGE = "com.hcph.sandexplore";

    // SAFETY: This service intentionally has no path or operation for level_save_1.dat.
    private static final File SAVE =
            new File("/sdcard/Android/data/com.hcph.sandexplore/files/save.dat");

    private static final File BACKUP_DIR =
            new File("/sdcard/Download/SandminerTrainerBackups");

    private static final File LATEST_POINTER =
            new File("/sdcard/Download/SandminerTrainerBackups/latest.txt");

    // Validated on Sand Miner 3.6.1.
    private static final int MONEY_OFFSET = 3030; // 0xBD6
    private static final int GEMS_OFFSET = 3047;  // 0xBE7

    // Stable bytes immediately before the gem Int32 in the validated 3.6.1 saves.
    private static final int SIGNATURE_OFFSET = 3039;
    private static final byte[] SIGNATURE = new byte[] {
            0x07, 0x00, 0x00, 0x00,
            0x04, 0x00, 0x00, 0x00
    };

    private static final int MIN_SAVE_SIZE = 50000;
    private static final int MAX_SAVE_SIZE = 500000;

    public SaveUserService() {
    }

    @Override
    public void destroy() {
        System.exit(0);
    }

    @Override
    public String getState() {
        try {
            byte[] data = readValidatedSave();
            return "OK|money=" + getInt(data, MONEY_OFFSET)
                    + "|gems=" + getInt(data, GEMS_OFFSET)
                    + "|size=" + data.length;
        } catch (Throwable t) {
            return error(t);
        }
    }

    @Override
    public String applyValues(int money, int gems) {
        try {
            validateRequestedValue("money", money);
            validateRequestedValue("gems", gems);

            forceStopGame();

            byte[] data = readValidatedSave();
            String backupName = createBackup();

            putInt(data, MONEY_OFFSET, money);
            putInt(data, GEMS_OFFSET, gems);

            writeExistingFile(SAVE, data);

            byte[] verify = readValidatedSave();
            int writtenMoney = getInt(verify, MONEY_OFFSET);
            int writtenGems = getInt(verify, GEMS_OFFSET);

            if (writtenMoney != money || writtenGems != gems) {
                restoreLatestInternal();
                return "ERR|Verification failed. Original save.dat was restored.";
            }

            return "OK|money=" + writtenMoney
                    + "|gems=" + writtenGems
                    + "|backup=" + backupName;
        } catch (Throwable t) {
            return error(t);
        }
    }

    @Override
    public String restoreLatest() {
        try {
            forceStopGame();
            String restored = restoreLatestInternal();
            byte[] data = readValidatedSave();
            return "OK|restored=" + restored
                    + "|money=" + getInt(data, MONEY_OFFSET)
                    + "|gems=" + getInt(data, GEMS_OFFSET);
        } catch (Throwable t) {
            return error(t);
        }
    }

    private static byte[] readValidatedSave() throws IOException {
        if (!SAVE.isFile()) {
            throw new IOException("Sand Miner save.dat was not found.");
        }

        long length = SAVE.length();
        if (length < MIN_SAVE_SIZE || length > MAX_SAVE_SIZE) {
            throw new IOException("Unexpected save.dat size: " + length);
        }

        byte[] data = readAll(SAVE);

        if (data.length <= GEMS_OFFSET + 3) {
            throw new IOException("save.dat is too short for the validated layout.");
        }

        for (int i = 0; i < SIGNATURE.length; i++) {
            if (data[SIGNATURE_OFFSET + i] != SIGNATURE[i]) {
                throw new IOException(
                        "Save layout is not the validated Sand Miner 3.6.1 format.");
            }
        }

        int money = getInt(data, MONEY_OFFSET);
        int gems = getInt(data, GEMS_OFFSET);

        if (money < 0 || gems < 0) {
            throw new IOException("Save values failed sanity validation.");
        }

        return data;
    }

    private static void validateRequestedValue(String name, int value) {
        if (value < 0) {
            throw new IllegalArgumentException(name + " must be zero or greater.");
        }
    }

    private static String createBackup() throws IOException {
        ensureBackupDirectory();

        String stamp = new SimpleDateFormat(
                "yyyyMMdd_HHmmss_SSS", Locale.US).format(new Date());

        File backup = new File(BACKUP_DIR, "save_" + stamp + ".dat");
        copyFile(SAVE, backup);

        try (FileWriter writer = new FileWriter(LATEST_POINTER, false)) {
            writer.write(backup.getAbsolutePath());
            writer.write("\n");
        }

        return backup.getName();
    }

    private static String restoreLatestInternal() throws IOException {
        ensureBackupDirectory();

        if (!LATEST_POINTER.isFile()) {
            throw new IOException("No Sandminer Trainer backup is available.");
        }

        String backupPath;
        try (BufferedReader reader = new BufferedReader(
                new FileReader(LATEST_POINTER))) {
            backupPath = reader.readLine();
        }

        if (backupPath == null || backupPath.trim().isEmpty()) {
            throw new IOException("Latest backup pointer is invalid.");
        }

        File backup = new File(backupPath.trim());

        if (!backup.isFile()) {
            throw new IOException("Latest save.dat backup is missing.");
        }

        byte[] data = readAll(backup);

        // Validate the trainer backup before putting it back into the game.
        if (data.length < MIN_SAVE_SIZE || data.length > MAX_SAVE_SIZE) {
            throw new IOException("Backup size validation failed.");
        }

        for (int i = 0; i < SIGNATURE.length; i++) {
            if (data[SIGNATURE_OFFSET + i] != SIGNATURE[i]) {
                throw new IOException("Backup layout validation failed.");
            }
        }

        writeExistingFile(SAVE, data);
        return backup.getName();
    }

    private static void ensureBackupDirectory() throws IOException {
        if (BACKUP_DIR.isDirectory()) {
            return;
        }

        if (!BACKUP_DIR.mkdirs() && !BACKUP_DIR.isDirectory()) {
            throw new IOException("Could not create trainer backup directory.");
        }
    }

    private static void forceStopGame() throws IOException, InterruptedException {
        Process process = new ProcessBuilder(
                "sh", "-c", "am force-stop " + GAME_PACKAGE).start();

        int result = process.waitFor();
        if (result != 0) {
            throw new IOException("Could not stop Sand Miner safely.");
        }
    }

    private static int getInt(byte[] data, int offset) {
        return ByteBuffer.wrap(data, offset, 4)
                .order(ByteOrder.LITTLE_ENDIAN)
                .getInt();
    }

    private static void putInt(byte[] data, int offset, int value) {
        ByteBuffer.wrap(data, offset, 4)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(value);
    }

    private static byte[] readAll(File file) throws IOException {
        try (FileInputStream input = new FileInputStream(file);
             ByteArrayOutputStream output =
                     new ByteArrayOutputStream((int) file.length())) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            return output.toByteArray();
        }
    }

    private static void writeExistingFile(File file, byte[] data)
            throws IOException {
        try (FileOutputStream output = new FileOutputStream(file, false)) {
            output.write(data);
            output.flush();
            FileDescriptor fd = output.getFD();
            fd.sync();
        }
    }

    private static void copyFile(File source, File destination)
            throws IOException {
        try (FileInputStream input = new FileInputStream(source);
             FileOutputStream output = new FileOutputStream(destination, false)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            output.flush();
            output.getFD().sync();
        }
    }

    private static String error(Throwable t) {
        String message = t.getMessage();
        if (message == null || message.trim().isEmpty()) {
            message = t.getClass().getSimpleName();
        }
        return "ERR|" + message.replace('|', '/')
                .replace('\n', ' ').replace('\r', ' ');
    }
}
