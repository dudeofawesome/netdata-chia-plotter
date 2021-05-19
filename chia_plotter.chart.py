from random import SystemRandom
from bases.FrameworkServices.SimpleService import SimpleService
import os
import subprocess
import glob

# try:
#   import plotman
#   HAS_PLOTMAN = True
# except ImportError:
#   HAS_PLOTMAN = False

NETDATA_UPDATE_EVERY = 15
priority = 90000

ORDER = [
    'in_prog_plots', 'farm_plots', 'plot_size', 'phase', 'state', 'wall'
]

CHARTS = {
    'in_prog_plots': {
        #           name  title                units    family   context  chart type
        'options': [None, 'Plots in progress', 'plots', 'plots', 'plots', 'area'],
        'lines': [
          # unique_name,    name,         algorithm, multiplier, divisor
          ['in_prog_plots', 'in progress'],
          ['paused_plots',  'paused',     None,      -1],
        ]
    },
    'farm_plots': {
        #           name  title                units    family   context  chart type
        'options': [None, 'Farm plots', 'plots', 'plots', 'plots', 'area'],
        #  unique_name,      name,       algorithm, multiplier, divisor
        'lines': [
          ['farmable_plots', 'farmable'],
          ['farming_plots',  'farming'],
        ]
    },
    'plot_size': {
        #           name  title                              units  family  context  chart type
        'options': [None, 'Local & whole network plot size', 'PiB', 'size', 'plots', 'area'],
        #  unique_name,       name,      algorithm, multiplier, divisor
        'lines': [
          ['local_plot_size', 'local',   None,      None,       1000000],
          ['network_size',    'network', None,      None,       None],
        ]
    },
    'phase': {
        #           name  title                         units               family   context  chart type
        'options': [None, 'The phase of the chia plot', 'chia plots phase', 'phase', 'phase', 'line'],
        'lines': []
    },
    'state': {
        #           name  title                         units              family   context  chart type
        'options': [None, 'The state of the chia plot', 'chia plot state', 'state', 'state', 'line'],
        'lines': []
    },
    'wall': {
        #           name  title        units    family  context chart type
        'options': [None, 'Who knows', 'hours', 'wall', 'wall', 'line'],
        'lines': []
    },
}


class Service(SimpleService):
  def __init__(self, configuration=None, name=None):
    SimpleService.__init__(self, configuration=configuration, name=name)
    self.order = ORDER
    self.definitions = CHARTS
    self.plot_path_globs = configuration.get('plot_path_globs', ['/mnt/*'])
    self.debug(self.plot_path_globs)

  def check(self):
    return True
    # if not HAS_PLOTMAN:
    #   self.error("'plotman' package is needed to use chia_plotter module")
    #   return False

  def get_data(self):
    data = dict()

    plots = read_plotman()
    self.debug(len(plots), 'plots in progress')

    data['paused_plots'] = len(list(filter(lambda plot: plot.state == 'STP', plots)))
    data['in_prog_plots'] = len(plots) - data['paused_plots']

    farmable_plots = get_farmable_plots(self.plot_path_globs)
    data['farmable_plots'] = len(farmable_plots)

    farm_summary = get_farm_summary(self)
    data['farming_plots'] = farm_summary.plot_count
    data['local_plot_size'] = farm_summary.total_plot_size * 1000000
    data['network_size'] = farm_summary.est_net_size

    for i in range(0, len(plots)):
      base_dimension_id = ''.join([plots[i].cache, ':', plots[i].id])
      phase_id = ''.join(['phase_', base_dimension_id])
      state_id = ''.join(['state_', base_dimension_id])
      wall_id = ''.join(['wall_', base_dimension_id])

      if phase_id not in self.charts['phase']:
        self.charts['phase'].add_dimension([phase_id, base_dimension_id, None, None, 10])
      if state_id not in self.charts['state']:
        self.charts['state'].add_dimension([state_id])
      if wall_id not in self.charts['wall']:
        self.charts['wall'].add_dimension([wall_id])

      phase = plots[i].phase.split(':')
      data[phase_id] = (float(phase[0]) + (float(phase[1]) / 10)) * 10.0

      # data[state_id] = plots[i].state

      # data[wall_id] = plots[i].wall

    return data

def read_plotman():
  lines = subprocess.run(
      ['cat', '/var/tmp/plotman-status.out'],
      # ['plotman', 'status'],
      # cwd='/usr/local/src/chia-blockchain',
      # # env=dict(PATH=''.join([os.getenv('PATH'),':/usr/bin:/bin:/usr/sbin:/sbin:/home/dudeofawesome/chia-blockchain/activate/bin'])),
      # env=dict(
      #   PATH=''.join([os.getenv('PATH'),':/usr/local/src/chia-blockchain/activate/bin']),
      #   VIRTUAL_ENV='/usr/local/src/chia-blockchain/activate',
      # ),
      capture_output=True,
      text=True,
    ).stdout.split('\n')
  lines = list(filter(lambda line: line != None and len(line) != 0, lines))
  lines = list(filter(lambda line: not line.strip().startswith('plot'), lines))

  for i in range(len(lines)):
    split = lines[i].split()
    if len(split) < 13:
      raise Exception(''.join(['Invalid input ', lines[i]]))

    lines[i] = Plot(
      id=split[0],
      k=split[1],
      cache=split[2],
      dest=split[3],
      wall=split[4],
      phase=split[5],
      cache_size=split[6],
      pid=split[7],
      state=split[8],
      memory=split[9],
      user=split[10],
      sys=split[11],
      io=split[12],
    )
  
  return lines

def get_farmable_plots(plot_path_globs):
  plots = []

  for plot_path_glob in plot_path_globs:
    for cache_dir in glob.glob(plot_path_glob):
      for plot in glob.glob(''.join([cache_dir, '/plots/*k32*.plot'])):
        plots.append(plot)  

  return plots

def get_farm_summary(self):
  summary_file_path = '/var/tmp/chia-farm-summary.out'
  if not os.path.isfile(summary_file_path):
    return
  summary_file = open(summary_file_path, 'r')
  summary_lines = summary_file.read().split('\n')
  summary_file.close()
  summary_hash = {}
  for line in summary_lines:
    if line != None and line != '':
      split = line.split(': ', maxsplit=1)
      summary_hash[split[0].lower()] = split[1]

  total_plot_size = None
  if 'total size of plots' in summary_hash:
    factor = conversion_factors_to_from['PiB'][summary_hash['total size of plots'][-3:]]
    total_plot_size = float(summary_hash['total size of plots'][0:-4]) * factor

  est_net_size = None
  if 'estimated network space' in summary_hash:
    factor = conversion_factors_to_from['PiB'][summary_hash['estimated network space'][-3:]]
    est_net_size = float(summary_hash['estimated network space'][0:-4]) * factor

  self.debug('TOTAL SIZE OF PLOTS')
  self.debug(summary_hash['total size of plots'])
  self.debug(total_plot_size, 'PiB')

  return FarmSummary(
    status =
      summary_hash['farming status'] if 'farming status' in summary_hash else None,
    chia_farmed =
      float(summary_hash['total chia farmed']) if 'total chia farmed' in summary_hash else None,
    transaction_fees =
      float(summary_hash['user transaction fees']) if 'user transaction fees' in summary_hash else None,
    block_rewards =
      float(summary_hash['block rewards']) if 'block rewards' in summary_hash else None,
    last_height_farmed =
      int(summary_hash['last height farmed']) if 'last height farmed' in summary_hash else None,
    plot_count =
      int(summary_hash['plot count']) if 'plot count' in summary_hash else None,
    total_plot_size = total_plot_size,
    est_net_size = est_net_size,
    etw =
      summary_hash['expected time to win'] if 'expected time to win' in summary_hash else None,
  )

class Plot():
  def __init__(
    self, id=None, k=None, cache=None, dest=None, wall=None, phase=None,
    cache_size=None, pid=None, state=None, memory=None, user=None, sys=None,
    io=None
  ):
    self.id = id
    self.k = k
    self.cache = cache
    self.dest = dest
    self.wall = wall
    self.phase = phase
    self.cache_size = cache_size
    self.pid = pid
    self.state = state
    self.memory = memory
    self.user = user
    self.sys = sys
    self.io = io

class FarmSummary():
  def __init__(
    self, status=None, chia_farmed=None, transaction_fees=None,
    block_rewards=None, last_height_farmed=None, plot_count=None,
    total_plot_size=None, est_net_size=None, etw=None
  ):
    self.status = status
    self.chia_farmed = chia_farmed
    self.transaction_fees = transaction_fees
    self.block_rewards = block_rewards
    self.last_height_farmed = last_height_farmed
    self.plot_count = plot_count
    self.total_plot_size = total_plot_size
    self.est_net_size = est_net_size
    self.etw = etw

conversion_factors_to_from = {
  'KiB': {
    'KiB': 1,
    'MiB': 1_024,
    'GiB': 1_048_576,
    'TiB': 1_073_741_824,
    'PiB': 1_099_511_627_776,
    'EiB': 1_125_899_906_842_624,
    'ZiB': 1_152_921_504_606_846_976,
  },
  'MiB': {
    'KiB': 1 / 1_024,
    'MiB': 1,
    'GiB': 1_024,
    'TiB': 1_048_576,
    'PiB': 1_073_741_824,
    'EiB': 1_099_511_627_776,
    'ZiB': 1_125_899_906_842_624,
  },
  'GiB': {
    'KiB': 1 / 1_048_576,
    'MiB': 1 / 1_024,
    'GiB': 1,
    'TiB': 1_024,
    'PiB': 1_048_576,
    'EiB': 1_073_741_824,
    'ZiB': 1_099_511_627_776,
  },
  'TiB': {
    'KiB': 1 / 1_073_741_824,
    'MiB': 1 / 1_048_576,
    'GiB': 1 / 1_024,
    'TiB': 1,
    'PiB': 1_024,
    'EiB': 1_048_576,
    'ZiB': 1_073_741_824,
  },
  'PiB': {
    'KiB': 1 / 1_099_511_627_776,
    'MiB': 1 / 1_073_741_824,
    'GiB': 1 / 1_048_576,
    'TiB': 1 / 1_024,
    'PiB': 1,
    'EiB': 1_024,
    'ZiB': 1_048_576,
  },
  'EiB': {
    'KiB': 1 / 1_125_899_906_842_624,
    'MiB': 1 / 1_099_511_627_776,
    'GiB': 1 / 1_073_741_824,
    'TiB': 1 / 1_048_576,
    'PiB': 1 / 1_024,
    'EiB': 1,
    'ZiB': 1_024,
  },
  'ZiB': {
    'KiB': 1 / 1_152_921_504_606_846_976,
    'MiB': 1 / 1_125_899_906_842_624,
    'GiB': 1 / 1_099_511_627_776,
    'TiB': 1 / 1_073_741_824,
    'PiB': 1 / 1_048_576,
    'EiB': 1 / 1_024,
    'ZiB': 1,
  },
}
