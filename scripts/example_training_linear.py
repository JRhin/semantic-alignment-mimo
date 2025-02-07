"""
This python module handles the training of the linear optimizer for SAE.

To check available parameters run 'python /path/to/example_training_linear.py --help'.
"""
# Add root to the path
import sys
import torch
from pathlib import Path
sys.path.append(str(Path(sys.path[0]).parent))

import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
from pytorch_lightning import seed_everything

from src.utils import complex_gaussian_matrix
from src.linear_models import  LinearOptimizerSAE
from src.datamodules import DataModule

def main():
    """The main loop.
    """
    import argparse

    description = """
    This python module handles the training of the linear optimizer for SAE.

    To check available parameters run 'python /path/to/example_training_linear.py --help'.
    """
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-d',
                        '--dataset',
                        help="The dataset.",
                        type=str,
                        required=True)

    parser.add_argument('--encoder',
                        help="The encoder.",
                        type=str,
                        required=True)

    parser.add_argument('--decoder',
                        help="The encoder.",
                        type=str,
                        required=True)

    parser.add_argument('-s',
                        '--snr',
                        help="The snr of the communication channel in dB. Set to None if unaware. Default None.",
                        type=float,
                        default=None)
    
    parser.add_argument('-t',
                        '--snr_type',
                        help="The typology of the snr. Default 'transmitted'.",
                        type=str,
                        default="transmitted",
                        choices=["transmitted", "received"])
    
    parser.add_argument('--transmitter',
                        help="The number of antennas for the transmitter.",
                        type=int,
                        required=True)
    
    parser.add_argument('--receiver',
                        help="The number of antennas for the receiver.",
                        type=int,
                        required=True)

    parser.add_argument('-i',
                        '--iterations',
                        help="The number of fitting iterations. Default None.",
                        type=int,
                        default=None)
    
    parser.add_argument('-c',
                        '--cost',
                        help="Transmission cost. Default 1.",
                        default=1,
                        type=int)

    parser.add_argument('--rho',
                        help="The rho parameter for admm. Default 1e2.",
                        default=1e2,
                        type=float)

    parser.add_argument('--seed',
                        help="The seed for the analysis. Default 42.",
                        default=42,
                        type=int)

    args = parser.parse_args()

    # Setting the seed
    seed_everything(args.seed, workers=True)

    # Get the channel matrix
    channel_matrix = complex_gaussian_matrix(mean=0, std=1, size=(args.receiver, args.transmitter))

    
    # =========================================================
    #                     Get the dataset
    # =========================================================
    # Initialize the datamodule
    datamodule = DataModule(dataset=args.dataset,
                            encoder=args.encoder,
                            decoder=args.decoder)
    
    # Prepare and setup the data
    datamodule.prepare_data()
    datamodule.setup()
    
    
    # =========================================================
    #               Define the Linear Optimizer
    # =========================================================
    opt = LinearOptimizerSAE(input_dim=datamodule.input_size,
                             output_dim=datamodule.output_size,
                             channel_matrix=channel_matrix,
                             snr=args.snr,
                             snr_type=args.snr_type,
                             cost=args.cost,
                             rho=args.rho)

    # Fit the linear optimizer
    losses, traces = opt.fit(input=datamodule.train_data.z,
                             output=datamodule.train_data.z_decoder,
                             iterations=args.iterations)
    
    # Eval the linear optimizer
    print("loss:",
          opt.eval(input=datamodule.test_data.z,
                   output=datamodule.test_data.z_decoder))

    print("trace(FF^H):", torch.trace(opt.F@opt.F.H).real.item())
    if args.cost:
        print(torch.trace(opt.F.H@opt.F).real.item() <= args.cost)

    pl.DataFrame({'Iterations':range(0, len(losses)),
                  'Losses': losses,
                  'Traces': traces}).write_parquet('convergence.parquet')

    print(pl.read_parquet('convergence.parquet'))
    
    fig, axs = plt.subplots(ncols=2, nrows=2)
    plot = sns.lineplot(x=range(0, len(losses)), y=losses, ax=axs[0, 0]).set(title="Convergence", ylabel="MSE Loss", xlabel="Iteration")
    plot = sns.lineplot(x=range(0, len(losses)), y=losses, ax=axs[0, 1]).set(title="Convergence Log Scaled", ylabel="MSE Loss", xlabel="Iteration", yscale='log')
    plot = sns.lineplot(x=range(0, len(traces)), y=traces, ax=axs[1, 0]).set(title="Convergence", ylabel="tr FF^H", xlabel="Iteration")
    plot = sns.lineplot(x=range(0, len(traces)), y=traces, ax=axs[1, 1]).set(title="Convergence Log Scaled", ylabel="tr FF^H", xlabel="Iteration", yscale='log')
    plt.show()

    return None

if __name__ == "__main__":
    main()
