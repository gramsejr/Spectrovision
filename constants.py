# -*- coding: ascii -*-
from __future__ import unicode_literals

import wx

VERSION = '1.02.005'

IS_GTK = 'wxGTK' in wx.PlatformInfo
IS_WIN = 'wxMSW' in wx.PlatformInfo
IS_MAC = 'wxMac' in wx.PlatformInfo

# mode
RELATIVE = 0
RT = 1
ENERGY_FLUX = 2
PHOTON_FLUX = 3
ILLUMINANCE = 4

SERVICED = False

MODE_TO_UNITS = ['Relative', 'Relative', 'Watts', 'umols', '%s']
UNITS_TO_STR = ['Lux', 'Footcandle']

# units. labels are written in latex math mode format for matplotlib. WX labels
# are written using unicode characters
WM2_LABEL = r'$Energy\ Flux\ Density\ [W\cdot m^{-2}\cdot nm^{-1}]$'
WX_WM2_LABEL = "[W\u2022m\u207B\u00b2\u2022nm\u207B\u00b9]"
MICROMOL_LABEL = r'$Photon\ Flux\ Density\ [\mu mol\cdot m^{-2}\cdot s^{-1}\cdot nm^{-1}]$'
WX_MICROMOL_LABEL = "[\u03BCmol\u2022m\u207B\u00b2\u2022s\u207B\u00b9\u2022nm" \
    "\u207B\u00b9]"
LUX = 0
LUX_LABEL = r'$Illuminance\ [lm\cdot m^{-2}\cdot nm^{-1}]$'
WX_LUX_LABEL = "[lm\u2022m\u207B\u00b2\u2022nm\u207B\u00b9]"
FOOTCANDLE = 1
FC_LABEL = r'$Illuminance\ [lm\cdot ft^{-2}\cdot nm^{-1}]$'
WX_FC_LABEL = "[lm\u2022ft\u207B\u00b2\u2022nm\u207B\u00b9]"
X_LABEL = r'$Wavelength\ [\lambda\ (nm)]$'

# used for ypf calculations. YPF = RF*PF
RQE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.005, 0.01,
       0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.015, 0.02,
       0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.07, 0.075,
       0.08, 0.085, 0.09, 0.095, 0.1, 0.105, 0.11, 0.115, 0.12,
       0.125, 0.13, 0.135, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2,
       0.21, 0.22, 0.235, 0.25, 0.26, 0.27, 0.285, 0.3, 0.315,
       0.33, 0.34, 0.35, 0.365, 0.38, 0.39, 0.4, 0.41, 0.42, 0.43,
       0.44, 0.45, 0.46, 0.47, 0.48, 0.49, 0.5, 0.51, 0.52, 0.53,
       0.54, 0.545, 0.55, 0.56, 0.57, 0.58, 0.59, 0.595, 0.6, 0.61,
       0.62, 0.625, 0.63, 0.64, 0.65, 0.655, 0.66, 0.665, 0.67,
       0.675, 0.68, 0.685, 0.69, 0.695, 0.7, 0.705, 0.71, 0.715,
       0.72, 0.725, 0.73, 0.735, 0.74, 0.74, 0.74, 0.745, 0.75,
       0.75, 0.75, 0.755, 0.76, 0.76, 0.76, 0.76, 0.76, 0.76, 0.76,
       0.76, 0.76, 0.76, 0.76, 0.755, 0.75, 0.75, 0.75, 0.75, 0.75,
       0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75,
       0.75, 0.75, 0.745, 0.74, 0.74, 0.74, 0.735, 0.73, 0.73,
       0.73, 0.725, 0.72, 0.715, 0.71, 0.705, 0.7, 0.7, 0.7, 0.695,
       0.69, 0.69, 0.69, 0.685, 0.68, 0.68, 0.68, 0.68, 0.68,
       0.685, 0.69, 0.69, 0.69, 0.69, 0.69, 0.69, 0.69, 0.69, 0.69,
       0.695, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.705, 0.71, 0.71,
       0.71, 0.71, 0.71, 0.71, 0.71, 0.715, 0.72, 0.72, 0.72, 0.72,
       0.72, 0.72, 0.72, 0.725, 0.73, 0.73, 0.73, 0.73, 0.73, 0.73,
       0.73, 0.735, 0.74, 0.74, 0.74, 0.745, 0.75, 0.75, 0.75,
       0.755, 0.76, 0.765, 0.77, 0.775, 0.78, 0.79, 0.8, 0.805,
       0.81, 0.815, 0.82, 0.825, 0.83, 0.835, 0.84, 0.845, 0.85,
       0.855, 0.86, 0.865, 0.87, 0.875, 0.88, 0.88, 0.88, 0.885,
       0.89, 0.895, 0.9, 0.905, 0.91, 0.91, 0.91, 0.915, 0.92,
       0.925, 0.93, 0.93, 0.93, 0.935, 0.94, 0.94, 0.94, 0.945,
       0.95, 0.95, 0.95, 0.955, 0.96, 0.96, 0.96, 0.965, 0.97,
       0.97, 0.97, 0.975, 0.98, 0.98, 0.98, 0.985, 0.99, 0.99,
       0.99, 0.99, 0.99, 0.995, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
       1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
       0.995, 0.99, 0.99, 0.99, 0.99, 0.99, 0.985, 0.98, 0.975,
       0.97, 0.97, 0.97, 0.965, 0.96, 0.955, 0.95, 0.95, 0.95,
       0.95, 0.95, 0.945, 0.94, 0.94, 0.94, 0.94, 0.94, 0.935,
       0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93,
       0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93, 0.925, 0.92, 0.92,
       0.92, 0.91, 0.9, 0.89, 0.88, 0.86, 0.84, 0.82, 0.8, 0.78,
       0.76, 0.735, 0.71, 0.685, 0.66, 0.635, 0.61, 0.59, 0.57,
       0.55, 0.53, 0.515, 0.5, 0.485, 0.47, 0.455, 0.44, 0.425,
       0.41, 0.4, 0.39, 0.38, 0.37, 0.355, 0.34, 0.33, 0.32, 0.315,
       0.31, 0.3, 0.29, 0.28, 0.27, 0.26, 0.25, 0.245, 0.24, 0.23,
       0.22, 0.215, 0.21, 0.2, 0.19, 0.185, 0.18, 0.17, 0.16, 0.15,
       0.14, 0.135, 0.13, 0.125, 0.12, 0.11, 0.1, 0.095, 0.09,
       0.085, 0.08, 0.075, 0.07, 0.065, 0.06, 0.06, 0.06, 0.05,
       0.04, 0.04, 0.04, 0.035, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03,
       0.03, 0.025, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
       0.015, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
       0.01, 0.01, 0.01, 0.01, 0.005, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
       0, 0, 0, 0, 0, 0, 0]

# both SIGMA_R and SIGMA_FR are used for PPE calculation
# PPE = PF*SIGMA_R/(PF*SIGMA_R + PF*SIGMA_RF)
SIGMA_R = [2233, 2035.5, 1838, 1747, 1656, 1577.5, 1499, 1455.5,
           1412, 1353, 1294, 1257.5, 1221, 1174, 1127, 1078, 1029,
           991, 953, 923, 893, 863.5, 834, 800.5, 767, 757, 747,
           736.5, 726, 719.5, 713, 713, 713, 719, 725, 738, 751,
           765.5, 780, 795.5, 811, 826, 841, 860, 879, 915.5, 952,
           970.5, 989, 1018.5, 1048, 1086, 1124, 1157, 1190,
           1226.5, 1263, 1294.5, 1326, 1357.5, 1389, 1412.5, 1436,
           1452, 1468, 1476, 1484, 1500.5, 1517, 1523, 1529,
           1534.5, 1540, 1542.5, 1545, 1561, 1577, 1577, 1577,
           1581.5, 1586, 1579, 1572, 1564.5, 1557, 1531, 1505,
           1484.5, 1464, 1422.5, 1381, 1337.5, 1294, 1254.5, 1215,
           1156, 1097, 1050.5, 1004, 954, 904, 857, 810, 771.5,
           733, 700.5, 668, 636, 604, 582.5, 561, 540, 519, 495,
           471, 449, 427, 417.5, 408, 387, 366, 357, 348, 334, 320,
           314, 308, 300, 292, 283, 274, 268.5, 263, 253.5, 244,
           244, 244, 237, 230, 230, 230, 219.5, 209, 202.5, 196,
           190, 184, 178, 172, 167, 162, 162, 162, 156, 150, 146.5,
           143, 135.5, 128, 128, 128, 123.5, 119, 119, 119, 113,
           107, 107, 107, 104, 101, 101, 101, 96.95, 92.9, 92.9,
           92.9, 88.75, 84.6, 84.6, 84.6, 84.6, 84.6, 79.7, 74.8,
           74.8, 74.8, 74.8, 74.8, 74.8, 74.8, 71.75, 68.7, 68.7,
           68.7, 68.7, 68.7, 68.7, 68.7, 68.7, 68.7, 72.85, 77, 77,
           77, 77, 77, 77, 77, 77, 77, 77, 77, 82.7, 88.4, 91.05,
           93.7, 101.85, 110, 110, 110, 109.5, 109, 115.5, 122,
           126, 130, 130, 130, 133.5, 137, 145, 153, 160.5, 168,
           168, 168, 177, 186, 194, 202, 211.5, 221, 230, 239,
           245.5, 252, 261, 270, 287, 304, 307.5, 311, 327, 343,
           356, 369, 386, 403, 412, 421, 428, 435, 451.5, 468, 486,
           504, 513.5, 523, 541.5, 560, 577.5, 595, 617.5, 640,
           659.5, 679, 707, 735, 762, 789, 816.5, 844, 876, 908,
           937.5, 967, 1009.5, 1052, 1087, 1122, 1161.5, 1201,
           1252.5, 1304, 1342.5, 1381, 1429, 1477, 1526.5, 1576,
           1620.5, 1665, 1705, 1745, 1780, 1815, 1854.5, 1894,
           1922, 1950, 1982.5, 2015, 2039, 2063, 2083.5, 2104,
           2122.5, 2141, 2162.5, 2184, 2215.5, 2247, 2275, 2303,
           2332, 2361, 2407.5, 2454, 2497, 2540, 2598.5, 2657,
           2730, 2803, 2860, 2917, 2993.5, 3070, 3145, 3220, 3319,
           3418, 3515.5, 3613, 3702, 3791, 3886.5, 3982, 4112,
           4242, 4343, 4444, 4534, 4624, 4755.5, 4887, 4988, 5089,
           5169.5, 5250, 5333.5, 5417, 5476, 5535, 5568, 5601,
           5591.5, 5582, 5550.5, 5519, 5420.5, 5322, 5218.5, 5115,
           4939.5, 4764, 4571, 4378, 4215, 4052, 3823, 3594,
           3356.5, 3119, 2904, 2689, 2498, 2307, 2106.5, 1906,
           1734.5, 1563, 1419.5, 1276, 1145, 1014, 911.5, 809, 729,
           649, 588, 527, 477, 427, 379, 331, 304, 277, 256.5, 236,
           211.5, 187, 178, 169, 158, 147, 141, 135, 126, 117, 110,
           103, 103, 103, 97.55, 92.1, 92.1, 92.1, 86.45, 80.8,
           80.8, 80.8, 77.05, 73.3, 73.3, 73.3, 73.3, 73.3, 73.3,
           73.3, 73.3, 73.3, 73.3, 73.3, 73.3, 73.3, 67.6, 61.9,
           61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9,
           61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9, 61.9,
           61.9, 61.9, 55.85, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8,
           49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8,
           49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8,
           49.8, 49.8, 49.8, 49.8, 49.8, 49.8, 49.8]

SIGMA_FR = [920, 852, 784, 745, 706, 687, 668, 656.5, 645, 627.5,
            610, 604.5, 599, 584, 569, 551.5, 534, 519.5, 505,
            486.5, 468, 450, 432, 412.5, 393, 381, 369, 354.5, 340,
            329.5, 319, 313.5, 308, 296.5, 285, 283, 281, 273.5,
            266, 262.5, 259, 258, 257, 256, 255, 253.5, 252, 254.5,
            257, 259, 261, 266, 271, 272.5, 274, 278, 282, 286.5,
            291, 296, 301, 306.5, 312, 319, 326, 330.5, 335, 342,
            349, 357, 365, 373, 381, 389, 397, 404, 411, 418.5,
            426, 434, 442, 446.5, 451, 457.5, 464, 474.5, 485,
            490.5, 496, 503.5, 511, 517.5, 524, 529, 534, 537, 540,
            546.5, 553, 556, 559, 561, 563, 565.5, 568, 569.5, 571,
            572, 573, 571.5, 570, 567, 564, 560.5, 557, 550, 543,
            535.5, 528, 517.5, 507, 498, 489, 471.5, 454, 442.5,
            431, 416, 401, 389, 377, 365, 353, 339, 325, 312.5,
            300, 286.5, 273, 267, 261, 247, 233, 225, 217, 209.5,
            202, 194, 186, 177.5, 169, 162, 155, 149.5, 144, 138,
            132, 129, 126, 119, 112, 109, 106, 102.55, 99.1, 96.1,
            93.1, 90.4, 87.7, 84.8, 81.9, 78.8, 75.7, 73.95, 72.2,
            72, 71.8, 67.15, 62.5, 60.15, 57.8, 55.45, 53.1, 51.35,
            49.6, 49.6, 49.6, 49.6, 49.6, 47.25, 44.9, 45.05, 45.2,
            43.4, 41.6, 41.6, 41.6, 39.25, 36.9, 36.9, 36.9, 36.7,
            36.5, 37.05, 37.6, 35.25, 32.9, 32.9, 32.9, 32.9, 32.9,
            32.9, 32.9, 33.1, 33.3, 30.3, 27.3, 26.85, 26.4, 26.4,
            26.4, 26.35, 26.3, 28.6, 30.9, 30.65, 30.4, 30.4, 30.4,
            30.2, 30, 29.6, 29.2, 28.8, 28.4, 28.4, 28.4, 30.65,
            32.9, 32.5, 32.1, 32.7, 33.3, 32.8, 32.3, 33.75, 35.2,
            34.75, 34.3, 36.8, 39.3, 39.15, 39, 38.15, 37.3, 40.6,
            43.9, 43, 42.1, 43.95, 45.8, 45.45, 45.1, 47.5, 49.9,
            52.75, 55.6, 55.1, 54.6, 57.95, 61.3, 60.4, 59.5,
            62.65, 65.8, 67.65, 69.5, 71.3, 73.1, 74.9, 76.7, 78.7,
            80.7, 82.45, 84.2, 88.6, 93, 94.05, 95.1, 97.4, 99.7,
            104.85, 110, 115.5, 121, 122.5, 124, 130, 136, 141,
            146, 147, 148, 152.5, 157, 159, 161, 166, 171, 175,
            179, 185.5, 192, 195.5, 199, 205.5, 212, 215, 218, 225,
            232, 238, 244, 250.5, 257, 263, 269, 275.5, 282, 291.5,
            301, 311, 321, 327, 333, 342.5, 352, 364, 376, 386,
            396, 406, 416, 427.5, 439, 449.5, 460, 472.5, 485,
            497.5, 510, 520.5, 531, 544.5, 558, 572.5, 587, 599,
            611, 622.5, 634, 647, 660, 670, 680, 692.5, 705, 714.5,
            724, 732, 740, 747, 754, 759.5, 765, 774.5, 784, 791,
            798, 803.5, 809, 817.5, 826, 834, 842, 849.5, 857,
            867.5, 878, 888.5, 899, 908, 917, 929.5, 942, 953.5,
            965, 979.5, 994, 1010.5, 1027, 1040.5, 1054, 1071.5,
            1089, 1107, 1125, 1138, 1151, 1173, 1195, 1213.5, 1232,
            1250, 1268, 1283, 1298, 1317.5, 1337, 1355.5, 1374,
            1389.5, 1405, 1421.5, 1438, 1448.5, 1459, 1471, 1483,
            1492.5, 1502, 1505, 1508, 1510.5, 1513, 1509, 1505,
            1496.5, 1488, 1477.5, 1467, 1451, 1435, 1414.5, 1394,
            1366, 1338, 1309.5, 1281, 1245, 1209, 1170.5, 1132,
            1094, 1056, 1019.5, 983, 943, 903, 871, 839, 788.5,
            738, 707.5, 677, 646.5, 616, 577.5, 539, 507, 475,
            448.5, 422, 394.5, 367, 344.5, 322, 304.5, 287, 267.5,
            248, 236, 224, 210, 196, 186.5, 177, 165, 153, 145.5,
            138, 134, 130, 123.5, 117, 109.5, 102, 97.1, 92.2,
            92.2, 92.2]

# used for illuminance calculations. LUX = EF*CIE_1931
CIE_1931 = [0.000039, 0.0000428264, 0.0000469146, 0.0000515896, 0.0000571764,
            0.000064, 0.00007234421, 0.00008221224, 0.00009350816, 0.0001061361,
            0.00012, 0.000134984, 0.000151492, 0.000170208, 0.000191816,
            0.000217, 0.0002469067, 0.00028124, 0.00031852, 0.0003572667,
            0.000396, 0.0004337147, 0.000473024, 0.000517876, 0.0005722187,
            0.00064, 0.00072456, 0.0008255, 0.00094116, 0.00106988, 0.00121,
            0.001362091, 0.001530752, 0.001720368, 0.001935323, 0.00218,
            0.0024548, 0.002764, 0.0031178, 0.0035264, 0.004, 0.00454624,
            0.00515932, 0.00582928, 0.00654616, 0.0073, 0.008086507, 0.00890872,
            0.00976768, 0.01066443, 0.0116, 0.01257317, 0.01358272, 0.01462968,
            0.01571509, 0.01684, 0.01800736, 0.01921448, 0.02045392, 0.02171824,
            0.023, 0.02429461, 0.02561024, 0.02695857, 0.02835125, 0.0298,
            0.03131083, 0.03288368, 0.03452112, 0.03622571, 0.038, 0.03984667,
            0.041768, 0.043766, 0.04584267, 0.048, 0.05024368, 0.05257304,
            0.05498056, 0.05745872, 0.06, 0.06260197, 0.06527752, 0.06804208,
            0.07091109, 0.0739, 0.077016, 0.0802664, 0.0836668, 0.0872328,
            0.09098, 0.09491755, 0.09904584, 0.1033674, 0.1078846, 0.1126,
            0.117532, 0.1226744, 0.1279928, 0.1334528, 0.13902, 0.1446764,
            0.1504693, 0.1564619, 0.1627177, 0.1693, 0.1762431, 0.1835581,
            0.1912735, 0.199418, 0.20802, 0.2171199, 0.2267345, 0.2368571,
            0.2474812, 0.2586, 0.2701849, 0.2822939, 0.2950505, 0.308578, 0.323,
            0.3384021, 0.3546858, 0.3716986, 0.3892875, 0.4073, 0.4256299,
            0.4443096, 0.4633944, 0.4829395, 0.503, 0.5235693, 0.544512,
            0.56569, 0.5869653, 0.6082, 0.6293456, 0.6503068, 0.6708752,
            0.6908424, 0.71, 0.7281852, 0.7454636, 0.7619694, 0.7778368,
            0.7932, 0.8081104, 0.8224962, 0.8363068, 0.8494916, 0.862,
            0.8738108, 0.8849624, 0.8954936, 0.9054432, 0.9148501, 0.9237348,
            0.9320924, 0.9399226, 0.9472252, 0.954, 0.9602561, 0.9660074,
            0.9712606, 0.9760225, 0.9803, 0.9840924, 0.9874182, 0.9903128,
            0.9928116, 0.9949501, 0.9967108, 0.9980983, 0.999112, 0.9997482,
            1, 0.9998567, 0.9993046, 0.9983255, 0.9968987, 0.995, 0.9926005,
            0.9897426, 0.9864444, 0.9827241, 0.9786, 0.9740837, 0.9691712,
            0.9638568, 0.9581349, 0.952, 0.9454504, 0.9384992, 0.9311628,
            0.9234576, 0.9154, 0.9070064, 0.8982772, 0.8892048, 0.8797816, 0.87,
            0.8598613, 0.849392, 0.838622, 0.8275813, 0.8163, 0.8047947,
            0.793082, 0.781192, 0.7691547, 0.757, 0.7447541, 0.7324224,
            0.7200036, 0.7074965, 0.6949, 0.6822192, 0.6694716, 0.6566744,
            0.6438448, 0.631, 0.6181555, 0.6053144, 0.5924756, 0.5796379,
            0.5668, 0.5539611, 0.5411372, 0.5283528, 0.5156323, 0.503,
            0.4904688, 0.4780304, 0.4656776, 0.4534032, 0.4412, 0.42908,
            0.417036, 0.405032, 0.393032, 0.381, 0.3689184, 0.3568272,
            0.3447768, 0.3328176, 0.321, 0.3093381, 0.2978504, 0.2865936,
            0.2756245, 0.265, 0.2547632, 0.2448896, 0.2353344, 0.2260528,
            0.217, 0.2081616, 0.1995488, 0.1911552, 0.1829744, 0.175, 0.1672235,
            0.1596464, 0.1522776, 0.1451259, 0.1382, 0.1315003, 0.1250248,
            0.1187792, 0.1127691, 0.107, 0.1014762, 0.09618864, 0.09112296,
            0.08626485, 0.0816, 0.07712064, 0.07282552, 0.06871008, 0.06476976,
            0.061, 0.05739621, 0.05395504, 0.05067376, 0.04754965, 0.04458,
            0.04175872, 0.03908496, 0.03656384, 0.03420048, 0.032, 0.02996261,
            0.02807664, 0.02632936, 0.02470805, 0.0232, 0.02180077, 0.02050112,
            0.01928108, 0.01812069, 0.017, 0.01590379, 0.01483718, 0.01381068,
            0.01283478, 0.01192, 0.01106831, 0.01027339, 0.009533311,
            0.008846157, 0.00821, 0.007623781, 0.007085424, 0.006591476,
            0.006138485, 0.005723, 0.005343059, 0.004995796, 0.004676404,
            0.004380075, 0.004102, 0.003838453, 0.003589099, 0.003354219,
            0.003134093, 0.002929, 0.002738139, 0.002559876, 0.002393244,
            0.002237275, 0.002091, 0.001953587, 0.00182458, 0.00170358,
            0.001590187, 0.001484, 0.001384496, 0.001291268, 0.001204092,
            0.001122744, 0.001047, 0.0009765896, 0.0009111088, 0.0008501332,
            0.0007932384, 0.00074, 0.0006900827, 0.00064331, 0.000599496,
            0.0005584547, 0.00052, 0.0004839136, 0.0004500528, 0.0004183452,
            0.0003887184, 0.0003611, 0.0003353835, 0.0003114404, 0.0002891656,
            0.0002684539, 0.0002492, 0.0002313019, 0.0002146856, 0.0001992884,
            0.0001850475, 0.0001719, 0.0001597781, 0.0001486044, 0.0001383016,
            0.0001287925, 0.00012, 0.0001118595, 0.0001043224, 0.0000973356,
            0.00009084587, 0.0000848, 0.00007914667, 0.000073858, 0.000068916,
            0.00006430267, 0.00006, 0.00005598187, 0.0000522256, 0.0000487184,
            0.00004544747, 0.0000424, 0.00003956104, 0.00003691512,
            0.00003444868, 0.00003214816, 0.00003, 0.00002799125,
            0.00002611356, 0.00002436024, 0.00002272461, 0.0000212,
            0.00001977855, 0.00001845285, 0.00001721687, 0.00001606459,
            0.00001499]

LUX_TO_FOOTCANDLES = 1/10.7693
LUX_MULTIPLIER = 638.002

# modbus and spec board details
DA_ADDR_IRRAD_UNIT = 0
DA_ADDR_COMMAND = 2
DA_ADDR_SCANS_AVG = 4
DA_ADDR_INTEGRATION = 6
DA_ADDR_STATUS = 8
DA_ADDR_GET_WAVELENGTHS = 10
DA_ADDR_POWER_MODE = 12
DA_ADDR_GET_TEMP = 39
DA_ADDR_STS_RESET = 49
DA_ADDR_MFG_MODE = 69
DA_ADDR_SPECTRUM = 100

CMD_UPDATE_DATA = 1.0
POWER_SAVE_ON = 1.0
POWER_SAVE_OFF = 0.0
RESET = 0.0
COUNTS = 0.0
WATTS_PER_METER_SQUARED = 1.0
MICRO_MOLES = 2.0
SECRET_UNLOCK_CODE = 6542.5445
LOCK_IN_CALIBRATION = 7843.4534
LOCK_IN_BAD_PIXELS = 1234.4321
CLEAR_BAD_PIXELS = 9876.5432
LOCK_IN_DARK_SCAN = 4321.1234
CLEAR_DARK_REFERENCE = 2345.6789

TOOLBAR_HELP = """
Toolbar
--------------------------------------------------------------------------------
Set dark reference:
During continuous measurement mode, this function will take the data from the last scan and save it as a dark reference to be used during both Relative and Reflectance/Transmittance plot modes. Otherwise, the application will take a new measurement to be used as the dark reference. If multiple devices are connected, the dark reference scan will apply only to the device selected in the toolbar.

Set light reference:
During continuous measurement mode, this function will take the data from the last scan and save it as a light reference to be used during Reflectance/Transmittance plot mode. Otherwise, the application will take a new measurement to be used as the light reference. If multiple devices are connected, the light reference scan will apply only to the device selected in the toolbar.

Clear dark reference:
Simply removes a saved dark reference scan from the selected device.

Open:
Opens a previously saved *.dat or *.csv file for plotting. This function supports opening multiple files at a time; however, only ten scans may be plotted at a time. These files must be saved in the correct format to be compatible with Apogee Spectrovision.

Save graph as image:
The current plot will be saved to an image file with the extension of your choice. Current supported extensions include *.pdf, *.jpg, *.png, *.ps, *.eps, and *.svg.

Save graph data:
The data of the current plot will be saved to a file of type *.csv or *.dat. This function supports multi sensor plots as well.

Save graph data and image:
Combines the previous two buttons in one for ease of use.

Copy graph to clipboard:
Copies the current plot to the system clipboard for pasting into other applications. The clipboard object is of type *.png.

Plot the first derivative:
Plots the first derivative of the current plot data. This button is only active if a single device is connected.

Plot the second derivative:
Plots the second derivative of the current plot data. This button is only active if a single device is connected.

Take a single measurement:
The device will take a single measurement and plot the data to the screen. This is a convenience function for manipulating the plot without the data being updated at an inopportune time.

Start continuous measurements:
The device will continually take measurements as soon as the data has been pulled from the previous scan. If multiple sensors are connected, measurements will wait until data has been pulled from all devices so that all measurements are taken at the same time.

Pause continuous measurements:
This simply pauses the continuous measurement mode. Use this function if you are worried about losing the data from the last scan but want to manipulate the currently displayed plot that may or may not represent the data from the last scan.

Stop continuous measurements:
This completely stops continuous measurements without regard to data being left in the device's buffer.

Sensor toggles:
When a device is connected, a new toggle button will be displayed on the toolbar representing the sensor. If the sensor is toggled, it is considered 'active' and all 'Set dark reference', 'Set light reference', and 'Clear dark reference' button clicks will apply only to the 'active' device. Right clicking on the device toggle button will display a pop up menu with options to rename the device, reset the device, or disconnect the device. If there is both a Visible and Near Infrared model connected, an additional option to pair the two together will be added to this menu. This will combine the two sensors to make a single plot from 340 nanometers to 1100 nanometers.
"""

LEFTPANEL_HELP = """
Left Panel Controls
--------------------------------------------------------------------------------

Integration Time:
This specifies the time frame the sensor is to use for integrating the received radiation. A longer integration time will give a greater signal. If the auto-integration toggle button is pressed, the device will specify its own integration time based on the received light intensity. Auto-integration will max out at 2 sec. For integration times greater than 2 sec, toggle Auto-Integration off and enter the desired time in the spin ctrl box. The Apogee Visible and NIR sensors support 0.005 - 10 second integration times. The last scans integration time will be displayed in the status bar at the bottom of the screen.

Number of Scans to Average
This tells the device how many measurements to average together before outputting data.

Relative:
Plots wavelength intensity as raw digital counts.

Reflectance/Transmittance:
Plots the reflectance or transmittance of a material. First requires that both a dark and light reference have been saved.

Energy Flux Density:
Plots in units of Watts/m^2*nm. This mode will also display an integrated total over the given Integration Range from the left panel.

Photon Flux Density:
Plots in units of micromole/m^2*s*nm. This mode will also display an integrated total over the given Integration Range from the left panel, as well as YPF, PPF, and PPE values.

Illuminance:
Plots a weighted data range in Lux or Footcandle according to user preference.

Integration Range:
These spin controls become active during Energy Flux Density and Photon Flux Density plot modes and are used to specify a customized wavelength integration range for the Integrated Total displayed on the plot. The YPF, PPF, and PPE values remain unchanged regardless of the Integration Range values. These controls are inactive for the other plot modes.

Fractional Range:
These spin controls become active during Energy Flux Density and Photon Flux Density modes. A 'Fractional' ratio is displayed on the graph. This ratio is the sum of the wavelengths specified in the Fractional Range spin controls divided by the sum of the wavelengths specified in the Integration Range spin controls.

Axes Limits:
These controls are inactive if the Auto Scale toggle button is active. The y axis has limits of (-16383, 16383) and the x axis has limits of (300, 1120). Any value in between may be specified with an accuracy of two decimal places.

Auto Scale:
Automatically scales the plot to include all data points. Can be toggled on or off.

Map Color Range:
Fills the area beneath the plot with the wavelength's corresponding color values. Can be toggled on or off. Keep toggled off to increase performance. This feature is disabled for multi-sensor/multi-line plots.

Reset Plot:
Resets the plot to original data with a generalized zoom range. Derivative data will be cleared as well. If Auto Scale or Map Color Range toggles have changed since last plot, the new settings will be applied.

Show Average:
This toggle button becomes active only if multiple lines are plotted at the same time either from a file, or from the Take a single measurement button in the toolbar. If this toggle is active, a thick black line will be plotted with the rest of the data representing the average.

Status Bar
--------------------------------------------------------------------------------

The first section on the far left displays tool tips when the cursor is over a menu bar option. The next section displays the currently active operation. The next section shows the active device's last integration time. The far right section of the status bar displays the current coordinates of the cursor in the plot area.

"""

MENUBAR_HELP = """
Menu Bar
--------------------------------------------------------------------------------

File

Data Capture:
The data capture feature allows for a functional data logging environment. The user may choose a specific number of measurements to record or leave it open ended by leaving the default value of 0 in the spin control. The user may specify a waiting period between measurements or if left at zero, the device will take measurements as soon as data has been pulled from memory. If 'Save data to file' is checked, the user will be prompted to enter a file name. If a previously created file is chosen, the data capture function will append new data to the end of the file. A different file must be chosen for each sensor currently connected to Apogee Spectrovision. If 'Plot data to screen' is checked, the data capture function will plot the first ten measurements of the file specified during data capture setup. If multiple sensors are connected and there are less than ten measurements in the first file, the next file will be read from until a max of 10 measurements have been accumulated for plotting. The data capture mode may be canceled at any time by hitting the 'Cancel' button. Any measurements made before hitting the 'Cancel' button will still be saved in the files specified during setup.

Connect:
This features connects to a sensor plugged in to the computers USB port. If more than one sensor is connected, the user will select which sensor to connect to from a dropdown menu.

Disconnect:
Disconnect from the device chosen from the dropdown menu.

Red/Far Red Setup:
Displays a window in which the user can specify the wavelength ranges of the Red and Far Red spectrums. The ratio R/RF (Red/Far Red) is displayed during Energy Flux Density and Photon Flux Density plot modes.

Exit:
Close the application.

View

Each option in this menu will switch the current plot mode to the one specified in the drop down menu. If continuous measurement mode is active, the next measurement taken will take on the new plot mode. Otherwise, a single measurement will be taken and plotted to the screen in the new plot mode.

Help

Jump to the help tab of the chosen subject.

Pressing the alt key while the application is open will display hot key values for menu bar options. For example, alt --> f --> c will select the Connect function in the File menu.
"""

PLOTVIEW_HELP = """
Plot View
--------------------------------------------------------------------------------

Buttons

Home:
Resets the plot zoom/pan position to the original position (before any other plot view button modifications).

Back:
Goes back to the previous view.

Forward:
Goes forward (if possible) to the next view.

Pan:
The 'Pan' toggle button allows the user to left click and drag to pan the plot. If the right button is clicked, the plot will scale in the direction of the drag instead of pan.

Zoom:
The zoom tool left click and drag will draw a zoom box in the plot area. Right click and drag will zoom out.

Plot Area Controls

A left click in the plot area will display the y-value of the plot near the data point and the corresponding x-value along the x-axis. A right click in the plot area will remove any labels displayed by a left-click. Scrolling in the plot area will zoom in or out depending on scroll direction.\n

"""

ABOUT_TEXT = """
Apogee Spectrovision - Version %s
Copyright \u00a9 2016 Apogee Instruments, Inc.


Apogee Spectrovision is a software package used to plot output from Apogee Spectrometers. This software provides users with an instant visual representation of data and has many useful features including saving data output, saving plot image, examining first and second derivatives, and short to long term data capture. Apogee Spectrovision provides multiple plot modes in a user friendly environment and supports multiple sensors connected in concert. This project was designed for cross platform use using Python, wxPython, Matplotlib, minimalmodbus, and pySerial libraries and has been tested on Windows 7, Windows 10, and OS X Yosemite.
""" % VERSION
