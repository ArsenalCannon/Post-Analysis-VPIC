!*******************************************************************************
! Main program.
!*******************************************************************************
program vdistribution
    use mpi_module
    use path_info, only: get_file_paths
    use picinfo, only: read_domain, broadcast_pic_info
    use particle_frames, only: get_particle_frames, nt, tinterval
    use spectrum_config, only: read_spectrum_config, set_spatial_range_de, &
            calc_pic_mpi_ids, tframe, init_pic_mpi_ranks, free_pic_mpi_ranks, &
            calc_pic_mpi_ranks
    use velocity_distribution, only: init_velocity_bins, free_velocity_bins, &
            init_vdist_2d, set_vdist_2d_zero, free_vdist_2d, init_vdist_1d, &
            set_vdist_1d_zero, free_vdist_1d, calc_vdist_2d, calc_vdist_1d
    use parameters, only: get_start_end_time_points, get_inductive_flag, &
            get_relativistic_flag
    implicit none
    integer :: ct
    ! Initialize Message Passing
    call MPI_INIT(ierr)
    call MPI_COMM_RANK(MPI_COMM_WORLD, myid, ierr)
    call MPI_COMM_SIZE(MPI_COMM_WORLD, numprocs, ierr)

    call get_file_paths
    if (myid==master) then
        call get_particle_frames
    endif
    call MPI_BCAST(nt, 1, MPI_INTEGER, 0, MPI_COMM_WORLD, ierr)
    call MPI_BCAST(tinterval, 1, MPI_INTEGER, 0, MPI_COMM_WORLD, ierr)

    if (myid==master) then
        call read_domain
    endif
    call broadcast_pic_info
    call get_start_end_time_points
    call get_inductive_flag
    call get_relativistic_flag
    call read_spectrum_config
    call set_spatial_range_de
    call calc_pic_mpi_ids
    call init_pic_mpi_ranks
    call calc_pic_mpi_ranks

    call init_velocity_bins
    call init_vdist_2d
    call init_vdist_1d

    call calc_vdist_2d(tframe, 'e')
    ! call set_vdist_2d_zero
    call calc_vdist_1d(tframe, 'e')
    ! call set_vdist_1d_zero

    call free_vdist_1d
    call free_vdist_2d
    call free_velocity_bins
    call free_pic_mpi_ranks
    call MPI_FINALIZE(ierr)
end program vdistribution
