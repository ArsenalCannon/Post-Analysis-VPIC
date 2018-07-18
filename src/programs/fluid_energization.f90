!<******************************************************************************
!< Energization due to fluid drifts and magnetization
!<******************************************************************************
program fluid_energization
    use mpi_module
    use constants, only: fp, dp
    use particle_info, only: species, get_ptl_mass_charge
    implicit none
    integer :: nvar, separated_pre_post, fd_tinterval
    character(len=256) :: rootpath
    integer :: ct

    ct = 1

    call init_analysis
    nvar = 7
    call energization_emf_ptensor
    nvar = 3
    call energization_para_perp_acc
    call end_analysis

    contains

    !<--------------------------------------------------------------------------
    !< Initialize the analysis
    !<--------------------------------------------------------------------------
    subroutine init_analysis
        use mpi_topology, only: set_mpi_topology, htg
        use mpi_datatype_fields, only: set_mpi_datatype_fields
        use mpi_info_module, only: set_mpi_info
        use particle_info, only: get_ptl_mass_charge
        use path_info, only: get_file_paths
        use picinfo, only: read_domain, broadcast_pic_info, &
                get_total_time_frames, get_energy_band_number, &
                read_thermal_params, calc_energy_interval, nbands, &
                write_pic_info, domain
        use configuration_translate, only: read_configuration
        use topology_translate, only: set_topology, set_start_stop_cells
        use mpi_io_translate, only: set_mpi_io
        use parameters, only: get_relativistic_flag, get_start_end_time_points, tp2
        use neighbors_module, only: init_neighbors, get_neighbors
        implicit none
        integer :: nx, ny, nz

        call MPI_INIT(ierr)
        call MPI_COMM_RANK(MPI_COMM_WORLD, myid, ierr)
        call MPI_COMM_SIZE(MPI_COMM_WORLD, numprocs, ierr)

        call get_cmd_args

        call get_file_paths(rootpath)
        if (myid == master) then
            call read_domain
        endif
        call broadcast_pic_info
        call get_ptl_mass_charge(species)
        call get_start_end_time_points
        call get_relativistic_flag
        ! call get_energy_band_number
        call read_thermal_params
        if (nbands > 0) then
            call calc_energy_interval
        endif
        call read_configuration
        call get_total_time_frames(tp2)
        call set_topology
        call set_start_stop_cells
        call set_mpi_io

        call set_mpi_topology(1)   ! MPI topology
        call set_mpi_datatype_fields
        call set_mpi_info

        call init_neighbors(htg%nx, htg%ny, htg%nz)
        call get_neighbors

    end subroutine init_analysis

    !<--------------------------------------------------------------------------
    !< End the analysis and free memory
    !<--------------------------------------------------------------------------
    subroutine end_analysis
        use topology_translate, only: free_start_stop_cells
        use mpi_io_translate, only: datatype
        use mpi_info_module, only: fileinfo
        use neighbors_module, only: free_neighbors
        use mpi_datatype_fields, only: filetype_ghost, filetype_nghost
        implicit none
        call free_neighbors
        call free_start_stop_cells
        call MPI_TYPE_FREE(datatype, ierror)
        call MPI_INFO_FREE(fileinfo, ierror)
        call MPI_TYPE_FREE(filetype_ghost, ierror)
        call MPI_TYPE_FREE(filetype_nghost, ierror)
        call MPI_FINALIZE(ierr)
    end subroutine end_analysis

    !<--------------------------------------------------------------------------
    !< Get commandline arguments
    !<--------------------------------------------------------------------------
    subroutine get_cmd_args
        use flap                                !< FLAP package
        use penf
        implicit none
        type(command_line_interface) :: cli     !< Command Line Interface (CLI).
        integer(I4P)                 :: error   !< Error trapping flag.
        call cli%init(progname    = 'fluid_drift_energization', &
                      authors     = 'Xiaocan Li', &
                      help        = 'Usage: ', &
                      description = 'Calculate energy conversion due to fluid drifts', &
                      examples    = ['fluid_drift_energization -rp simulation_root_path'])
        call cli%add(switch='--rootpath', switch_ab='-rp', &
            help='simulation root path', required=.true., act='store', error=error)
        if (error/=0) stop
        call cli%add(switch='--species', switch_ab='-sp', &
            help='particle species', required=.false., act='store', &
            def='e', error=error)
        if (error/=0) stop
        call cli%add(switch='--separated_pre_post', switch_ab='-pp', &
            help='separated pre and post fields', required=.false., act='store', &
            def='1', error=error)
        if (error/=0) stop
        call cli%add(switch='--fd_tinterval', switch_ab='-ft', &
            help='Frame interval when dumping 3 continuous frames', &
            required=.false., def='1', act='store', error=error)
        if (error/=0) stop
        call cli%get(switch='-rp', val=rootpath, error=error)
        if (error/=0) stop
        call cli%get(switch='-sp', val=species, error=error)
        if (error/=0) stop
        call cli%get(switch='-pp', val=separated_pre_post, error=error)
        if (error/=0) stop
        call cli%get(switch='-ft', val=fd_tinterval, error=error)
        if (error/=0) stop

        if (myid == 0) then
            print '(A,A)', 'The simulation rootpath: ', trim(adjustl(rootpath))
            print '(A,A)', 'Partical species: ', species
            if (separated_pre_post) then
                print '(A)', 'Fields at previous and next time steps are saved separately'
                print '(A, I0)', 'Frame interval between previous and current step is: ', &
                    fd_tinterval
            endif
        endif
    end subroutine get_cmd_args

    !<--------------------------------------------------------------------------
    !< Calculate energization due to curvature drift, gradient drift,
    !< magnetization, compression energization, and shear energization.
    !< These energization terms use electric field, magnetic field and pressure
    !< tensor.
    !<--------------------------------------------------------------------------
    subroutine energization_emf_ptensor
        use mpi_topology, only: htg
        use picinfo, only: domain
        use particle_info, only: species
        use para_perp_pressure, only: init_para_perp_pressure, &
            free_para_perp_pressure, calc_real_para_perp_pressure
        use pic_fields, only: init_electric_fields, init_magnetic_fields, &
            init_pressure_tensor, free_magnetic_fields, free_electric_fields, &
            free_pressure_tensor, open_magnetic_field_files, &
            open_electric_field_files, open_pressure_tensor_files, &
            close_magnetic_field_files, close_electric_field_files, &
            close_pressure_tensor_files, read_magnetic_fields, &
            read_electric_fields, read_pressure_tensor, &
            interp_emf_node, shift_pressure_tensor
        use fluid_energization_module, only: init_tmp_data, init_neighbors, &
            free_tmp_data, free_neighbors, get_neighbors, &
            curv_drift_energization, grad_drift_energization, &
            magnetization_energization, compression_shear_energization
        use saving_flags, only: get_saving_flags
        use configuration_translate, only: output_format
        use parameters, only: tp1, tp2
        implicit none
        integer :: tframe, nframes, posf, fh1, tindex
        real(fp), allocatable, dimension(:, :) :: jdote, jdote_tot
        character(len=256) :: fname
        logical :: dir_e

        call get_ptl_mass_charge(species)
        call get_saving_flags
        call init_electric_fields(htg%nx, htg%ny, htg%nz)
        call init_magnetic_fields(htg%nx, htg%ny, htg%nz)
        call init_pressure_tensor(htg%nx, htg%ny, htg%nz)
        call init_para_perp_pressure

        if (output_format == 1) then
            call open_magnetic_field_files
            call open_electric_field_files
            call open_pressure_tensor_files(species)
        endif

        call init_tmp_data
        call init_neighbors
        call get_neighbors

        nframes = tp2 - tp1 + 1
        allocate(jdote(nframes, nvar))
        allocate(jdote_tot(nframes, nvar))

        jdote = 0.0
        jdote_tot = 0.0

        do tframe = tp1, tp2
            if (myid==master) print*, tframe
            if (output_format /= 1) then
                tindex = domain%fields_interval * (tframe - tp1)
                call open_magnetic_field_files(tindex)
                call open_electric_field_files(tindex)
                call open_pressure_tensor_files(species, tindex)
                call read_magnetic_fields(tp1)
                call read_electric_fields(tp1)
                call read_pressure_tensor(tp1)
            else
                call read_magnetic_fields(tframe)
                call read_electric_fields(tframe)
                call read_pressure_tensor(tframe)
            endif
            if (output_format /= 1) then
                call close_magnetic_field_files
                call close_electric_field_files
                call close_pressure_tensor_files
            endif
            call interp_emf_node
            call shift_pressure_tensor
            call calc_real_para_perp_pressure(tframe)
            jdote(tframe - tp1 + 1, 1) = curv_drift_energization()
            jdote(tframe - tp1 + 1, 2) = grad_drift_energization()
            jdote(tframe - tp1 + 1, 3) = magnetization_energization()
            ! This part is very dangerous, because it modifies the pressure
            ! data. So be careful if you are going to use pressure data again.
            jdote(tframe - tp1 + 1, 4:7) = compression_shear_energization()
        enddo

        call MPI_REDUCE(jdote, jdote_tot, nframes * nvar, &
                MPI_REAL, MPI_SUM, master, MPI_COMM_WORLD, ierr)
        if (myid == master) then
            inquire(file='./data/fluid_energization/.', exist=dir_e)
            if (.not. dir_e) then
                call system('mkdir -p ./data/fluid_energization/')
            endif
            print*, "Saving fluid-based energization..."

            fh1 = 67

            fname = 'data/fluid_energization/emf_ptensor_'//species//".gda"
            open(unit=fh1, file=fname, access='stream', status='unknown', &
                form='unformatted', action='write')
            posf = 1
            write(fh1, pos=posf) nvar + 0.0
            posf = posf + 4
            write(fh1, pos=posf) nframes + 0.0
            posf = posf + 4
            write(fh1, pos=posf) jdote_tot
            close(fh1)
        endif

        deallocate(jdote, jdote_tot)

        call free_tmp_data
        call free_neighbors

        if (output_format == 1) then
            call close_magnetic_field_files
            call close_electric_field_files
            call close_pressure_tensor_files
        endif

        call free_para_perp_pressure
        call free_magnetic_fields
        call free_electric_fields
        call free_pressure_tensor
    end subroutine energization_emf_ptensor

    !<--------------------------------------------------------------------------
    !< Calculate energization due to parallel electric field, perpendicular
    !< electric field, and fluid acceleration
    !<--------------------------------------------------------------------------
    subroutine energization_para_perp_acc
        use mpi_topology, only: htg
        use picinfo, only: domain
        use particle_info, only: species
        use pic_fields, only: init_electric_fields, init_magnetic_fields, &
            init_ufields, init_vfields, init_number_density, &
            free_magnetic_fields, free_electric_fields, free_ufields, &
            free_vfields, free_number_density, open_magnetic_field_files, &
            open_electric_field_files, open_ufield_files, open_vfield_files, &
            open_number_density_file, close_magnetic_field_files, &
            close_electric_field_files, close_ufield_files, close_vfield_files, &
            close_number_density_file, read_magnetic_fields, &
            read_electric_fields, read_ufields, read_vfields, read_number_density, &
            interp_emf_node, shift_ufields, shift_vfields, shift_number_density
        use fluid_energization_module, only: init_tmp_data, init_neighbors, &
            free_tmp_data, free_neighbors, get_neighbors, para_perp_energization, &
            fluid_accel_energization
        use pre_post_hydro, only: init_pre_post_u, free_pre_post_u, &
            open_ufield_pre_post, close_ufield_pre_post, read_pre_post_u, &
            shift_ufield_pre_post
        use saving_flags, only: get_saving_flags
        use configuration_translate, only: output_format
        use parameters, only: tp1, tp2
        implicit none
        integer :: tframe, nframes, posf, fh1
        integer :: tindex, tindex_pre, tindex_post
        real(fp), allocatable, dimension(:, :) :: jdote, jdote_tot
        real(fp) :: dt_fields
        character(len=256) :: fname
        logical :: dir_e

        call get_ptl_mass_charge(species)
        call get_saving_flags
        call init_electric_fields(htg%nx, htg%ny, htg%nz)
        call init_magnetic_fields(htg%nx, htg%ny, htg%nz)
        call init_ufields(htg%nx, htg%ny, htg%nz)
        call init_vfields(htg%nx, htg%ny, htg%nz)
        call init_number_density(htg%nx, htg%ny, htg%nz)
        call init_pre_post_u(htg%nx, htg%ny, htg%nz)

        if (output_format == 1) then
            call open_magnetic_field_files
            call open_electric_field_files
            call open_ufield_files(species)
            call open_vfield_files(species)
            call open_number_density_file(species)
            call open_ufield_pre_post(species, separated_pre_post)
        endif

        call init_tmp_data
        call init_neighbors
        call get_neighbors

        nframes = tp2 - tp1 + 1
        allocate(jdote(nframes, nvar))
        allocate(jdote_tot(nframes, nvar))

        jdote = 0.0
        jdote_tot = 0.0

        do tframe = tp1, tp2
            if (myid==master) print*, tframe
            if (output_format /= 1) then
                tindex = domain%fields_interval * (tframe - tp1)
                if (tframe == tp1) then
                    tindex_pre = tindex
                else
                    tindex_pre = tindex - 1
                endif
                if (tframe == tp2) then
                    tindex_post = tindex
                else
                    tindex_post = tindex + 1
                endif
                call open_magnetic_field_files(tindex)
                call open_electric_field_files(tindex)
                call open_ufield_files(species, tindex)
                call open_vfield_files(species, tindex)
                call open_number_density_file(species, tindex)
                call open_ufield_pre_post(species, separated_pre_post, &
                    tindex, tindex_pre, tindex_post)
                call read_magnetic_fields(tp1)
                call read_electric_fields(tp1)
                call read_ufields(tp1)
                call read_vfields(tp1)
                call read_number_density(tp1)
                call read_pre_post_u(tp1, output_format, separated_pre_post)
            else
                call read_magnetic_fields(tframe)
                call read_electric_fields(tframe)
                call read_ufields(tframe)
                call read_vfields(tframe)
                call read_number_density(tframe)
                call read_pre_post_u(tframe, output_format, separated_pre_post)
            endif
            if (output_format /= 1) then
                call close_magnetic_field_files
                call close_electric_field_files
                call close_ufield_files
                call close_vfield_files
                call close_number_density_file
                call close_ufield_pre_post
            endif
            call interp_emf_node
            call shift_ufields
            call shift_vfields
            call shift_number_density
            call shift_ufield_pre_post
            if (separated_pre_post) then
                if (tframe == tp1) then
                    dt_fields = domain%dtwpe
                else if (tframe == tp2) then
                    dt_fields = domain%dtwpe * fd_tinterval
                else
                    dt_fields = domain%dtwpe * fd_tinterval * 2.0
                endif
            else
                if (tframe == tp1 .or. tframe == tp2) then
                    dt_fields = domain%dt
                else
                    dt_fields = domain%dt * 2.0
                endif
            endif
            jdote(tframe - tp1 + 1, 1) = fluid_accel_energization(dt_fields)
            jdote(tframe - tp1 + 1, 2:3) = para_perp_energization()
        enddo

        call MPI_REDUCE(jdote, jdote_tot, nframes * nvar, &
                MPI_REAL, MPI_SUM, master, MPI_COMM_WORLD, ierr)
        if (myid == master) then
            inquire(file='./data/fluid_energization/.', exist=dir_e)
            if (.not. dir_e) then
                call system('mkdir -p ./data/fluid_energization/')
            endif
            print*, "Saving energization due to fluid acceleration..."

            fh1 = 67

            fname = 'data/fluid_energization/para_perp_acc_'//species//".gda"
            open(unit=fh1, file=fname, access='stream', status='unknown', &
                form='unformatted', action='write')
            posf = 1
            write(fh1, pos=posf) nvar + 0.0
            posf = posf + 4
            write(fh1, pos=posf) nframes + 0.0
            posf = posf + 4
            write(fh1, pos=posf) jdote_tot
            close(fh1)
        endif

        deallocate(jdote, jdote_tot)

        call free_tmp_data
        call free_neighbors

        if (output_format == 1) then
            call close_magnetic_field_files
            call close_electric_field_files
            call close_ufield_files
            call close_vfield_files
            call close_number_density_file
            call close_ufield_pre_post
        endif

        call free_pre_post_u
        call free_magnetic_fields
        call free_electric_fields
        call free_ufields
        call free_vfields
        call free_number_density
    end subroutine energization_para_perp_acc

end program fluid_energization
