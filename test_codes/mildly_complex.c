#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    int rank, size;
    int N = 1000000;
    double *data = NULL;
    double local_sum = 0.0, global_sum = 0.0;
    double t0, t1;

    MPI_Init(&argc, &argv);

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    /* Rank 0 chooses the problem size */
    if (rank == 0 && argc > 1)
        N = atoi(argv[1]);

    /* Broadcast to everyone */
    MPI_Bcast(&N, 1, MPI_INT, 0, MPI_COMM_WORLD);

    data = malloc(N * sizeof(double));

    for (int i = 0; i < N; i++)
        data[i] = rank + 0.001 * i;

    MPI_Barrier(MPI_COMM_WORLD);
    t0 = MPI_Wtime();

    /* Local computation */
    for (int i = 0; i < N; i++)
        local_sum += data[i];

    /* Sum over all processes */
    MPI_Reduce(&local_sum, &global_sum, 1,
               MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    /* Ring communication */
    int send = rank;
    int recv = -1;

    MPI_Sendrecv(&send, 1, MPI_INT,
                 (rank + 1) % size, 0,
                 &recv, 1, MPI_INT,
                 (rank - 1 + size) % size, 0,
                 MPI_COMM_WORLD, MPI_STATUS_IGNORE);

    t1 = MPI_Wtime();

    printf("Rank %d received %d from its left neighbor\n",
           rank, recv);

    if (rank == 0) {
        printf("Processes : %d\n", size);
        printf("Array size: %d\n", N);
        printf("Global sum: %.3f\n", global_sum);
        printf("Elapsed   : %.6f seconds\n", t1 - t0);
    }

    free(data);

    MPI_Finalize();
    return 0;
}
