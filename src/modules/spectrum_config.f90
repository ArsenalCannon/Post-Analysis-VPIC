!*******************************************************************************
! Module of the initial setup, including the energy bins, the maximum and
! minimum of the particle energy, the energy interval (both linear and
! logarithmic), the center of the box (de), the sizes of the box (cells).
!*******************************************************************************
module spectrum_config
    use constants, only: fp, dp
    implicit none
    private
    public nbins, emax, emin, dve, dlogve, spatial_range, center, sizes, &
           tot_pic_mpi, pic_mpi_ranks, config_name
    public read_spectrum_config, set_spatial_range_de, calc_pic_mpi_ids, &
           calc_energy_interval, init_pic_mpi_ranks, free_pic_mpi_ranks, &
           calc_pic_mpi_ranks, set_time_frame
    public corners_mpi, vmax, vmin, vmin_nonzero, dv, dv_log, nbins_vdist, tframe
    public calc_velocity_interval
    integer :: nbins
    real(fp) :: emax, emin, dve, dlogve
    real(fp) :: vmax, vmin, vmin_nonzero
    real(fp) :: dv, dv_log                      ! For velocity distribution.
    integer :: nbins_vdist
    integer :: tframe                           ! Time frame.
    real(fp), dimension(3) :: center            ! In electron skin length (de).
    real(fp), dimension(3) :: sizes             ! In number of cells.
    real(fp), dimension(2,3) :: spatial_range   ! In electron skin length (de).
    integer, dimension(2,3) :: corners_mpi      ! MPI IDs of the corners.
    integer :: tot_pic_mpi                      ! Total number of PIC MPI process.
    integer, allocatable, dimension(:) :: pic_mpi_ranks  ! PIC MPI rank in 1D.
    character(len=64) :: config_name

    interface set_spatial_range_de
        module procedure &
            set_spatial_range_by_cener_size, set_spatial_range_by_lims
    end interface set_spatial_range_de

    contains

    !<--------------------------------------------------------------------------
    !< Read the setup information from file.
    !< Args:
    !<  spect_config_name: spectrum configuration filename
    !<--------------------------------------------------------------------------
    subroutine read_spectrum_config(spect_config_name)
        use mpi_module
        use read_config, only: get_variable
        implicit none
        character(*), intent(in), optional :: spect_config_name
        integer :: fh
        real(fp) :: temp
        fh = 10
        if (present(spect_config_name)) then
            open(unit=fh, file=spect_config_name, status='old')
        else
            open(unit=fh, file='config_files/spectrum_config.dat', status='old')
        endif
        temp = get_variable(fh, 'nbins', '=')   ! Number of energy bins
        nbins = int(temp)
        emax = get_variable(fh, 'emax', '=')    ! Maximum energy
        emin = get_variable(fh, 'emin', '=')    ! Minimum energy
        center(1) = get_variable(fh, 'xc/de', '=') ! x-coord of the box center
        center(2) = get_variable(fh, 'yc/de', '=') ! y-coord
        center(3) = get_variable(fh, 'zc/de', '=') ! z-coord
        sizes(1) = get_variable(fh, 'xsize', '=')  ! Number of cells along x
        sizes(2) = get_variable(fh, 'ysize', '=')
        sizes(3) = get_variable(fh, 'zsize', '=')
        temp = get_variable(fh, 'nbins_vdist', '=')
        nbins_vdist = int(temp)
        vmax = get_variable(fh, 'vmax', '=')
        vmin = get_variable(fh, 'vmin', '=')
        vmin_nonzero = get_variable(fh, 'vmin_nonzero', '=')
        temp = get_variable(fh, 'tframe', '=')
        tframe = int(temp)
        close(fh)

        call calc_energy_interval

        if (myid == 0) then
            ! Echo this information
            print *, "---------------------------------------------------"
            write(*, "(A)") " Spectrum and velocity distribution information."
            write(*, "(A,I0)") " Number of energy bins = ", nbins
            write(*, "(A,E14.6,E14.6)") " Minimum and maximum energy(gamma) = ", &
                emin, emax
            write(*, "(A,3F6.2)") " Center of the box (de) = ", center
            write(*, "(A,3F10.2)") " Sizes of the box (cells) = ", sizes
            write(*, "(A,I0)") " Number of velocity bins = ", nbins_vdist
            write(*, "(A,F6.2,F6.2)") " Minimum and maximum velocity(gamma) = ", &
                vmin, vmax
            write(*, "(A,E14.6,E14.6)") " Minimum and maximum velocity(gamma) for log scale = ", &
                vmin_nonzero, vmax
            write(*, "(A,I0)") " Time frame of velocity distribution = ", tframe
            print *, "---------------------------------------------------"
        endif

    end subroutine read_spectrum_config

    !---------------------------------------------------------------------------
    ! Set time frame
    ! Input:
    !   ct: time frame for fields.
    !---------------------------------------------------------------------------
    subroutine set_time_frame(ct)
        use picinfo, only: domain
        implicit none
        integer, intent(in) :: ct
        integer :: ratio_particle_field
        ratio_particle_field = domain%Particle_interval / domain%fields_interval
        tframe = ct / ratio_particle_field
    end subroutine set_time_frame

    !---------------------------------------------------------------------------
    ! Calculate the energy interval for each energy bin.
    !---------------------------------------------------------------------------
    subroutine calc_energy_interval
        implicit none
        dve = emax/real(nbins)  ! Linear-scale interval
        dlogve = (log10(emax)-log10(emin))/real(nbins)  ! Logarithmic-scale.
    end subroutine calc_energy_interval

    !---------------------------------------------------------------------------
    ! Calculate velocity integral.
    !---------------------------------------------------------------------------
    subroutine calc_velocity_interval
        implicit none
        dv      = (vmax - vmin) / nbins_vdist
        dv_log  = (log10(vmax) - log10(vmin_nonzero)) / (nbins_vdist - 1)
    end subroutine calc_velocity_interval

    !---------------------------------------------------------------------------
    ! Initialize the pic_mpi_ranks 1D array.
    !---------------------------------------------------------------------------
    subroutine init_pic_mpi_ranks
        implicit none
        allocate(pic_mpi_ranks(tot_pic_mpi))
        pic_mpi_ranks = 0
    end subroutine init_pic_mpi_ranks

    !---------------------------------------------------------------------------
    ! Calculate the pic_mpi_ranks 1D array.
    !---------------------------------------------------------------------------
    subroutine calc_pic_mpi_ranks
        use picinfo, only: domain
        implicit none
        integer :: i, j, k, tx, ty, tz, index1
        tx = domain%pic_tx
        ty = domain%pic_ty
        tz = domain%pic_tz
        index1 = 0
        do k = corners_mpi(1, 3), corners_mpi(2, 3)
            do j = corners_mpi(1, 2), corners_mpi(2, 2)
                do i = corners_mpi(1, 1), corners_mpi(2, 1)
                    index1 = index1 + 1
                    pic_mpi_ranks(index1) = i + j*tx + k*tx*ty
                enddo
            enddo
        enddo
    end subroutine calc_pic_mpi_ranks

    !---------------------------------------------------------------------------
    ! Free the pic_mpi_ranks 1D array.
    !---------------------------------------------------------------------------
    subroutine free_pic_mpi_ranks
        implicit none
        deallocate(pic_mpi_ranks)
    end subroutine free_pic_mpi_ranks

    !---------------------------------------------------------------------------
    ! As the xsize, ysize, zsize are in number of cell, we shall set the spatial
    ! range in electron skin length (de). The spatial range is decided by the
    ! center and sizes of the box.
    !---------------------------------------------------------------------------
    subroutine set_spatial_range_by_cener_size
        use picinfo, only: domain
        implicit none
        real(fp) :: dx, dy, dz, lx, ly, lz
        dx = domain%dx
        dy = domain%dy
        dz = domain%dz
        lx = domain%lx_de
        ly = domain%ly_de
        lz = domain%lz_de
        ! x
        spatial_range(1, 1) = center(1) - 0.5*sizes(1)*dx
        spatial_range(2, 1) = center(1) + 0.5*sizes(1)*dx
        if (spatial_range(1, 1) < 0.0) spatial_range(1, 1) = 0.0
        if (spatial_range(2, 1) > lx) spatial_range(2, 1) = lx
        ! y
        spatial_range(1, 2) = center(2) - 0.5*sizes(2)*dy
        spatial_range(2, 2) = center(2) + 0.5*sizes(2)*dy
        if (spatial_range(1, 2) < -ly/2) spatial_range(1, 2) = -ly/2
        if (spatial_range(2, 2) > ly/2) spatial_range(2, 2) = ly/2
        ! z
        spatial_range(1, 3) = center(3) - 0.5*sizes(3)*dz
        spatial_range(2, 3) = center(3) + 0.5*sizes(3)*dz
        if (spatial_range(1, 3) < -lz/2) spatial_range(1, 3) = -lz/2
        if (spatial_range(2, 3) > lz/2) spatial_range(2, 3) = lz/2
    end subroutine set_spatial_range_by_cener_size

    !---------------------------------------------------------------------------
    ! Set the spatial range based on the xlim and zlim of a box.
    ! Current version only limit the x and z directions. To make sure the limits
    ! of the y-direction are not zeros, set_spatial_range_by_lims is called
    ! first.
    ! Input:
    !   xlim, zlim: limitation along the x and z directions (in di).
    !---------------------------------------------------------------------------
    subroutine set_spatial_range_by_lims(xlim, zlim)
        use picinfo, only: mime, domain
        implicit none
        real(dp), intent(in), dimension(2) :: xlim, zlim
        real(fp) :: smime
        call set_spatial_range_by_cener_size
        smime = sqrt(mime)
        spatial_range(:, 1) = xlim * smime
        spatial_range(:, 3) = zlim * smime
        center(1) = sum(xlim) * smime * 0.5
        center(3) = sum(zlim) * smime * 0.5
        sizes(1) = (xlim(2) - xlim(1)) * smime * domain%idx
        sizes(3) = (zlim(2) - zlim(1)) * smime * domain%idz
    end subroutine set_spatial_range_by_lims

    !---------------------------------------------------------------------------
    ! Calculate the IDs of the MPI processes which contains the bottom-left
    ! and top-right corners of the box. The MPI processes are in the MPI
    ! topology of the PIC simulation.
    !---------------------------------------------------------------------------
    subroutine calc_pic_mpi_ids
        use picinfo, only: domain
        implicit none
        real(dp) :: cx, cy, cz
        cx = center(1) * domain%idx
        cy = (center(2) + domain%ly_de*0.5) * domain%idy
        cz = (center(3) + domain%lz_de*0.5) * domain%idz
        corners_mpi(1, 1) = floor((cx-sizes(1)*0.5)/domain%pic_nx)
        corners_mpi(1, 2) = floor((cy-sizes(2)*0.5)/domain%pic_ny)
        corners_mpi(1, 3) = floor((cz-sizes(3)*0.5)/domain%pic_nz)
        if (corners_mpi(1, 1) < 0) corners_mpi(1, 1) = 0
        if (corners_mpi(1, 2) < 0) corners_mpi(1, 2) = 0
        if (corners_mpi(1, 3) < 0) corners_mpi(1, 3) = 0

        corners_mpi(2, 1) = floor((cx+sizes(1)*0.5)/domain%pic_nx)
        corners_mpi(2, 2) = floor((cy+sizes(2)*0.5)/domain%pic_ny)
        corners_mpi(2, 3) = floor((cz+sizes(3)*0.5)/domain%pic_nz)
        if (corners_mpi(2, 1) > domain%pic_tx-1) corners_mpi(2, 1) = domain%pic_tx-1
        if (corners_mpi(2, 2) > domain%pic_ty-1) corners_mpi(2, 2) = domain%pic_ty-1
        if (corners_mpi(2, 3) > domain%pic_tz-1) corners_mpi(2, 3) = domain%pic_tz-1
        tot_pic_mpi = (corners_mpi(2, 1) - corners_mpi(1, 1) + 1) * &
                      (corners_mpi(2, 2) - corners_mpi(1, 2) + 1) * &
                      (corners_mpi(2, 3) - corners_mpi(1, 3) + 1)
    end subroutine calc_pic_mpi_ids

end module spectrum_config
