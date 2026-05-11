%% Filnavn
ribbe_file = "Ribbe-test_1(in).csv";
strain_file = "strain_log_viktig 3.csv";

%% Leser ribbetest-fil
ribbe_data = readmatrix(ribbe_file, "NumHeaderLines", 2);

% Kolonner fra ribbetest
time_ribbe = ribbe_data(:,1);   
force = ribbe_data(:,3);        

%% Leser strain-log fil
strain_data = readmatrix(strain_file);

% Kolonner fra strain_log
time_strain_ms = strain_data(:,1);   
microstrain = strain_data(:,3);      

%% Gjør om millisekund til sekunder
time_strain = time_strain_ms / 1000;

%% SYNKRONISERING AV SIGNALENE

% Tidspunkt for knekk i force-graf
force_knekk_tid = 60;

% Tidspunkt for samme knekk i microstrain-graf
strain_knekk_tid = 270;

% Flytt microstrain-tidsakse
time_strain_shifted = ...
    time_strain - strain_knekk_tid + force_knekk_tid;

%% REGN OM MICROSTRAIN TIL DISPLACEMENT

% Målelengde [mm]
L_mm = 50;

% Gjør om microstrain til strain
strain = microstrain * 1e-6;

% Beregn displacement i mm
displacement_mm = strain * L_mm;

%% Lag større figur
figure('Position',[100 100 1400 1000])

%% -----------------------------
%% Subplot 1 - Force
%% -----------------------------
subplot(3,1,1)

plot(time_ribbe, force, ...
    'LineWidth', 2)

grid on

xlabel('Time [s]')
ylabel('Force [kN]')

title('Force vs Time')

xlim([0 180])

% Gjør tekst større
ax = gca;

ax.FontSize = 26;
ax.FontWeight = 'normal';

ax.XLabel.FontSize = 30;
ax.YLabel.FontSize = 30;

ax.Title.FontSize = 32;
ax.Title.FontWeight = 'normal';

%% -----------------------------
%% Subplot 2 - Microstrain
%% -----------------------------
subplot(3,1,2)

plot(time_strain_shifted, microstrain, ...
    'LineWidth', 2)

grid on

xlabel('Time [s]')
ylabel('Microstrain [ue]')

title('Microstrain vs Time')

xlim([0 180])

% Gjør tekst større
ax = gca;

ax.FontSize = 26;
ax.FontWeight = 'normal';

ax.XLabel.FontSize = 30;
ax.YLabel.FontSize = 30;

ax.Title.FontSize = 32;
ax.Title.FontWeight = 'normal';

%% -----------------------------
%% Subplot 3 - Displacement
%% -----------------------------
subplot(3,1,3)

plot(time_strain_shifted, displacement_mm, ...
    'LineWidth', 2)

grid on

xlabel('Time [s]')
ylabel('Displacement [mm]')

title('Displacement vs Time')

xlim([0 180])

% Gjør tekst større
ax = gca;

ax.FontSize = 26;
ax.FontWeight = 'normal';

ax.XLabel.FontSize = 30;
ax.YLabel.FontSize = 30;

ax.Title.FontSize = 32;
ax.Title.FontWeight = 'normal';