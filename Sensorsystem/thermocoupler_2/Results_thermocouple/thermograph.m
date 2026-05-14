%% plot_oven.m
%  Plot reflow oven thermocouple test data
clear; clc; close all;

% ============================================================
%  SETTINGS
% ============================================================
FILE        = 'log_2026-04-26_164914.csv';
TITLE_TEXT  = 'Thermocouple Reflow Oven Test — Temperature Response and Stability';
X_LABEL     = 'Time (s)';
Y_LABEL     = 'Temperature (°C)';
Y_MAX       = 280;
Y_TICK      = 20;

% Oven stage boundaries
T1_START    = 405;   % t1 countdown starts (oven beeps at C1)
T1_END      = 585;   % t1 ends, oven raises to C2
C1_SETPOINT = 200;
C2_SETPOINT = 250;

% Colors
COL_TC  = [0.161 0.502 0.725];   % blue - hot junction
COL_CJ  = [0.133 0.694 0.298];   % green - cold junction
COL_C1  = [0.906 0.298 0.235];   % red - C1 setpoint
COL_C2  = [0.800 0.400 0.000];   % orange - C2 setpoint

% ============================================================
%  LOAD DATA
% ============================================================
time_s = [];
temp_tc = [];
temp_cj = [];

fid = fopen(FILE, 'r');
while ~feof(fid)
    line = fgetl(fid);
    if ~ischar(line), continue, end
    line = strtrim(strrep(line, char(13), ''));
    if isempty(line) || line(1) == '=', continue, end
    parts = strsplit(line, ',');
    if numel(parts) == 4
        v = str2double(parts(1:3));
        if ~any(isnan(v))
            time_s(end+1,1)  = v(1) / 1000;
            temp_tc(end+1,1) = v(2);
            temp_cj(end+1,1) = v(3);
        end
    end
end
fclose(fid);

% Normalize time to start from 0
time_s = time_s - time_s(1);

fprintf('Samples: %d, Duration: %.0fs\n', length(time_s), time_s(end));

% ============================================================
%  STATISTICS
% ============================================================
t1_mask  = time_s >= T1_START & time_s <= T1_END;
t2_mask  = time_s > T1_END;

t1_mean  = mean(temp_tc(t1_mask));
t2_max   = max(temp_tc(t2_mask));
t2_final = mean(temp_tc(end-20:end-5));

fprintf('C1 hold mean: %.2fC\n', t1_mean);
fprintf('C2 max reached: %.2fC\n', t2_max);
fprintf('C2 final stable: %.2fC\n', t2_final);

% ============================================================
%  PLOT
% ============================================================
figure('Name', TITLE_TEXT, 'NumberTitle', 'off', ...
    'Position', [100 100 1100 550]);
hold on; grid on;
set(gca, 'GridLineStyle', '--', 'GridAlpha', 0.4);

x_max = time_s(end) + 5;

% Shaded regions
fill([T1_START; T1_END; T1_END; T1_START], ...
     [0; 0; Y_MAX; Y_MAX], ...
     [0.9 0.9 0.9], 'FaceAlpha', 0.3, 'EdgeColor', 'none', ...
     'DisplayName', 'C1 hold phase (t1)');

fill([T1_END; x_max; x_max; T1_END], ...
     [0; 0; Y_MAX; Y_MAX], ...
     [0.8 0.8 1.0], 'FaceAlpha', 0.2, 'EdgeColor', 'none', ...
     'DisplayName', 'C2 hold phase (t2)');

% Setpoint lines
plot([0 x_max], [C1_SETPOINT C1_SETPOINT], ...
     '--', 'Color', COL_C1, 'LineWidth', 1.0, ...
     'DisplayName', sprintf('C1 setpoint (%d°C)', C1_SETPOINT));

plot([0 x_max], [C2_SETPOINT C2_SETPOINT], ...
     '--', 'Color', COL_C2, 'LineWidth', 1.0, ...
     'DisplayName', sprintf('C2 setpoint (%d°C)', C2_SETPOINT));

% Stage boundary line
plot([T1_START T1_START], [0 Y_MAX], ...
     'k:', 'LineWidth', 0.8, 'HandleVisibility', 'off');
plot([T1_END T1_END], [0 Y_MAX], ...
     'k:', 'LineWidth', 0.8, 'HandleVisibility', 'off');

% Data lines
plot(time_s, temp_tc, '-', 'Color', COL_TC, 'LineWidth', 1.5, ...
     'DisplayName', 'Hot junction (Type N thermocouple)');
plot(time_s, temp_cj, '--', 'Color', COL_CJ, 'LineWidth', 1.0, ...
     'DisplayName', 'Cold junction (ambient)');

% ============================================================
%  ANNOTATIONS
% ============================================================
% Stage labels
text(T1_START + 10, Y_MAX - 15, 't_1 hold', ...
     'FontSize', 9, 'Color', [0.3 0.3 0.3]);
text(T1_END + 10, Y_MAX - 15, 't_2 hold', ...
     'FontSize', 9, 'Color', [0.3 0.3 0.3]);
text(10, Y_MAX - 15, 'Ramp to C_1', ...
     'FontSize', 9, 'Color', [0.3 0.3 0.3]);

% C1 hold annotation
text(T1_START + 10, t1_mean - 15, ...
     sprintf('Mean: ~%.1f°C\n(Setpoint: %d°C)', t1_mean, C1_SETPOINT), ...
     'Color', COL_TC, 'FontSize', 9, ...
     'BackgroundColor', 'white', ...
     'EdgeColor', COL_TC, 'Margin', 3);

% C2 max annotation
[~, t2_max_idx] = max(temp_tc(t2_mask));
t2_time = time_s(t2_mask);
text(t2_time(t2_max_idx) - 60, t2_max + 8, ...
     sprintf('Max: ~%.1f°C\n(Setpoint: %d°C)', t2_max, C2_SETPOINT), ...
     'Color', COL_TC, 'FontSize', 9, ...
     'BackgroundColor', 'white', ...
     'EdgeColor', COL_TC, 'Margin', 3);

% ============================================================
%  FORMATTING
% ============================================================
hold off;
xlabel(X_LABEL, 'FontSize', 12);
ylabel(Y_LABEL, 'FontSize', 12);
title(TITLE_TEXT, 'FontSize', 13, 'FontWeight', 'bold');
legend('Location', 'northwest', 'FontSize', 9);
ylim([0 Y_MAX]);
yticks(0:Y_TICK:Y_MAX);
xlim([0 x_max]);

% ============================================================
%  SAVE
% ============================================================
exportgraphics(gcf, 'thermocouple_oven_test.pdf', 'ContentType', 'vector');
fprintf('Figure saved as thermocouple_oven_test.pdf\n');