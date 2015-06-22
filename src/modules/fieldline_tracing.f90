!*******************************************************************************
! This module includes procedures to trace magnetic field lines.
! We only consider 2D domain in x-z plane here.
!*******************************************************************************
module fieldline_tracing
    use constants, only: fp

    implicit none
    private
    public nx, nz, gdx, gdz, lx, lz, Bx, By, Bz, a, b, c, dc
    public read_whole_field, init_fieldline_tracing, end_fieldline_tracing, &
           read_magnetic_fields, tracing, get_crossing_point, controller, &
           push, grid_indices, derivs, Cash_Karp_parameters, &
           Dormand_Prince_parameters
    
    integer :: nx, nz
    real(fp) :: gdx, gdz, lx, lz    ! Grid sizes and lengths in di.
    real(fp), allocatable, dimension(:,:) :: Bx, By, Bz
    ! Adaptive Runge-Kutta parameters.
    real(fp), dimension(0:6) :: a, c, dc
    real(fp), dimension(0:5,0:6) :: b

    contains

    !---------------------------------------------------------------------------
    ! Read the whole data of one 2D field at current time frame.
    ! Input:
    !   filename: the file name of the data.
    !   ct: current time frame.
    !   nx, nz: the sizes of the 2D field.
    ! Return:
    !   fdata: field data.
    !---------------------------------------------------------------------------
    subroutine read_whole_field(filename, ct, nx, nz, fdata)
        use constants, only: fp, dp
        use parameters, only: it1
        implicit none
        character(*), intent(in) :: filename
        integer, intent(in) :: ct, nx, nz
        real(fp), dimension(nx, nz), intent(out) :: fdata
        integer(dp) :: pos1
        open(unit=101, file=filename, access='stream',&
            status='unknown', form='unformatted', action='read')
        pos1 = nx * nz * sizeof(fp) * (ct-it1) + 1
        read(101, pos=pos1) fdata
        close(101)
    end subroutine read_whole_field

    !---------------------------------------------------------------------------
    ! Initialize the magnetic field.
    !---------------------------------------------------------------------------
    subroutine init_magnetic_fields
        implicit none
        allocate(Bx(nx, nz))
        allocate(By(nx, nz))
        allocate(Bz(nx, nz))
        Bx = 0.0
        Bz = 0.0
        Bz = 0.0
    end subroutine init_magnetic_fields

    !---------------------------------------------------------------------------
    ! Free the magnetic field.
    !---------------------------------------------------------------------------
    subroutine free_magnetic_fields
        implicit none
        deallocate(Bx, By, Bz)
    end subroutine free_magnetic_fields

    !---------------------------------------------------------------------------
    ! Set the grid information, including the grid sizes and grid lengths.
    !---------------------------------------------------------------------------
    subroutine set_grid_info
        use constants, only: fp
        use picinfo, only: domain, mime
        implicit none

        nx = domain%nx
        nz = domain%nz

        gdx = domain%dx / sqrt(mime)
        gdz = domain%dz / sqrt(mime)
        lx = domain%lx_de / sqrt(mime)
        lz = domain%lz_de / sqrt(mime)
    end subroutine set_grid_info

    !---------------------------------------------------------------------------
    ! Initialize field line tracing, including setting the grid information,
    ! initializing magnetic field and read magnetic field.
    !---------------------------------------------------------------------------
    subroutine init_fieldline_tracing
        implicit none
        call set_grid_info
        call init_magnetic_fields
    end subroutine init_fieldline_tracing

    !---------------------------------------------------------------------------
    ! Finish field line tracing by freeing the magnetic field.
    !---------------------------------------------------------------------------
    subroutine end_fieldline_tracing
        implicit none
        call free_magnetic_fields
    end subroutine end_fieldline_tracing

    !---------------------------------------------------------------------------
    ! Read the magnetic field using the master MPI process and broadcast to
    ! other MPI processes.
    !---------------------------------------------------------------------------
    subroutine read_magnetic_fields(ct)
        use path_info, only: rootpath
        use mpi_module
        implicit none
        integer, intent(in) :: ct
        if (myid == master) then
            call read_whole_field(trim(adjustl(rootpath))//'data/bx.gda', &
                ct, nx, nz, Bx)
            call read_whole_field(trim(adjustl(rootpath))//'data/by.gda', &
                ct, nx, nz, By)
            call read_whole_field(trim(adjustl(rootpath))//'data/bz.gda', &
                ct, nx, nz, Bz)
        endif
        call MPI_BCAST(Bx, nx*nz, MPI_REAL, master, MPI_COMM_WORLD, ierr)
        call MPI_BCAST(By, nx*nz, MPI_REAL, master, MPI_COMM_WORLD, ierr)
        call MPI_BCAST(Bz, nx*nz, MPI_REAL, master, MPI_COMM_WORLD, ierr)
    end subroutine read_magnetic_fields

    !---------------------------------------------------------------------------
    ! Trace magnetic field line starting at one point. The length of the field
    ! line is used as the variable, so Bx/dx = By/dy = Bz/dz = B/ds.
    ! Inputs:
    !   htry: the first-try step size.
    ! Inputs & Outputs:
    !   x, z: the coordinates of current point.
    ! Outputs:
    !   np: total number of points along the field line.
    !   xarr, zarr: the arrays of coordinates along the field line.
    ! References:
    !   Press, William H. Numerical recipes 3rd edition: The art of scientific
    !   computing. Cambridge university press, 2007. Chapter 17.2.
    !---------------------------------------------------------------------------
    subroutine tracing(x, z, htry, np, xarr, zarr)
        use constants, only: fp
        implicit none
        real(fp), intent(inout) :: x, z
        real(fp), intent(in) :: htry
        integer, intent(out) :: np
        real(fp), dimension(:), intent(out) :: xarr, zarr
        real(fp), dimension(0:6) :: kx, ky, kz
        real(fp) :: arc_length, xout, zout, xold, zold
        real(fp) :: xcross, zcross
        real(fp) :: dxds, dyds, dzds, dxdsnew, dydsnew, dzdsnew
        real(fp) :: h, hnext, errold
        logical :: is_accept

        arc_length = 0.0
        h = htry
        errold = 1.0e-4
        is_accept = .false.
        np = 1

        xarr(np) = x
        zarr(np) = z

        call derivs(x, z, dxds, dyds, dzds)
        do while (x > 0 .and. x < lx .and. z > 0 .and. z < lz .and. &
                  arc_length < 2*lx)
            call push(dxds, dyds, dzds, x, z, h, kx, ky, kz, &
                      xout, zout, dxdsnew, dydsnew, dzdsnew)
            call controller(h, hnext, x, z, xout, zout, kx, kz, is_accept, errold)
            if (is_accept) then
                arc_length = arc_length + h
                xold = x
                zold = z
                x = xout
                z = zout
                dxds = dxdsnew
                dyds = dydsnew
                dzds = dzdsnew
                h = hnext
                np = np + 1
                xarr(np) = x
                zarr(np) = z
            endif
        enddo ! while loop

        ! Make sure it integrates to the boundary.
        if (x < 0 .or. x > lx .or. z < 0 .or. z > lz) then
            ! This excludes the closed field inside the domain.
            xcross = 0.0
            zcross = 0.0
            call get_crossing_point(x, z, xold, zold, lx, lz, xcross, zcross)
            h = sqrt((xcross-xold)**2 + (zcross-zold)**2)
            arc_length = arc_length + h
            call push(dxds, dyds, dzds, x, z, h, kx, ky, kz, &
                      xout, zout, dxdsnew, dydsnew, dzdsnew)
            np = np + 1
            xarr(np) = x
            zarr(np) = z
        endif
    end subroutine tracing

    !---------------------------------------------------------------------------
    ! Get the boundary crossing point.
    ! Inputs:
    !   x, z: the position of the point outside the box.
    !   xold, zold: the position of the point inside the box.
    !   lx, lz: the sizes of the box.
    ! Outputs:
    !   xcross, zcross: the crossing point.
    !---------------------------------------------------------------------------
    subroutine get_crossing_point(x, z, xold, zold, lx, lz, xcross, zcross)
        use constants, only: fp
        implicit none
        real(fp), intent(in) :: x, z, xold, zold, lx, lz
        real(fp), intent(out) :: xcross, zcross
        real(fp) :: k, xb, xt, zr, zl
        if ((x-xold) /= 0.0) then
            k = (z-zold) / (x-xold)
            xb = xold - zold/k       ! Bottom
            if (xb >= 0 .and. xb <= lx .and. z < 0.0 .and. zold > 0.0) then
                xcross = xb
                zcross = 0.0
                return
            endif
            xt = xold + (lz-zold)/k  ! Top
            if (xt >= 0 .and. xt <= lx .and. z > lz .and. zold < lz) then
                xcross = xt
                zcross = lz
                return
            endif
            zr = k*(lx-xold) + zold  ! Right
            if (zr >= 0 .and. zr <= lz .and. x > lx .and. xold < lx) then
                xcross = lx
                zcross = zr
                ! print*, xold, zold, x, z, xcross, zcross
                return
            endif
            zl = -k*xold + zold      ! Left
            if (zl >= 0 .and. zl <= lz .and. x < 0.0 .and. xold > 0.0) then
                xcross = 0.0
                zcross = zl
                return
            endif
        else
            ! Vertical line
            if (z >= lz) then
                xcross = x
                zcross = lz
            else
                xcross = x
                zcross = 0
            endif
        endif
    end subroutine get_crossing_point

    !---------------------------------------------------------------------------
    ! Controller of the step size update the points.
    !---------------------------------------------------------------------------
    subroutine controller(h, hnext, x, z, xout, zout, kx, kz, is_accept, errold)
        use constants, only: fp
        implicit none
        real(fp), intent(in) :: x, z, xout, zout
        real(fp), intent(in), dimension(0:6) :: kx, kz
        real(fp), intent(out) :: hnext
        logical, intent(inout) :: is_accept
        real(fp), intent(inout) :: h, errold
        real(fp) :: err_tot, sk
        real(fp) :: errx, errz, sscale
        !real(fp), parameter :: TINY=1.0e-30, SAFETY=0.9, PGROW=-0.2
        !real(fp), parameter :: PSHRNK=-0.25, ERRCON=1.89e-4
        real(fp), parameter :: beta=0.0, alpha=0.2-beta*0.75, safe=0.9
        real(fp), parameter :: minscale=0.2, maxscale=10.0
        real(fp), parameter :: atol = 1.0E-5, rtol = 1.0E-5
        ! Estimate current error and current maximum error.
        err_tot = 0.0
        errx = sum(kx(2:6)*dc(2:6))*h + kx(0)*dc(0)*h
        sk = atol + rtol*max(abs(x), abs(xout))
        err_tot = err_tot + (errx/sk)**2
        errz = sum(kz(2:6)*dc(2:6))*h + kz(0)*dc(0)*h
        sk = atol + rtol*max(abs(z), abs(zout))
        err_tot = err_tot + (errz/sk)**2
        err_tot = sqrt(err_tot*0.5)
        if (err_tot <= 1.0) then
            if (err_tot == 0.0) then
                sscale = maxscale
            else
                sscale = safe * err_tot**(-alpha) * errold**beta
                ! Ensure minscale <= hnext/h <= hnext/h
                if (sscale < minscale) then
                    sscale = minscale
                endif
                if (sscale > maxscale) then
                    sscale = maxscale
                endif
            endif
            if (.not. is_accept) then
                ! Don't increase if last one was rejected.
                hnext = h * min(sscale, 1.0)
            else
                hnext = h * sscale
            endif
            ! Bookkeeping for next call
            errold = max(err_tot, 1.0e-4)
            is_accept = .true.
        else
            sscale = max(safe*err_tot**(-alpha), minscale);
            h = h * sscale
            is_accept = .false.
        endif
    end subroutine controller

    !---------------------------------------------------------------------------
    ! Adaptive Runge-Kutta procedures.
    ! Inputs:
    !   dxds, dyds, dzds: the direction of the field line.
    !   x, z: current position.
    !   h: the step size.
    ! Outputs:
    !   kx, ky, kz: the dxds, dyds, dzds at the middle points.
    !   exs, eys, ezs: the electric fields at the middle points.
    !   xout, zout: the updated position.
    !---------------------------------------------------------------------------
    subroutine push(dxds, dyds, dzds, x, z, h, kx, ky, kz, &
                    xout, zout, dxdsnew, dydsnew, dzdsnew)
        use constants, only: fp
        implicit none
        real(fp), intent(in) :: dxds, dyds, dzds, x, z, h
        real(fp), dimension(0:6), intent(out) :: kx, ky, kz
        real(fp), intent(out) :: xout, zout, dxdsnew, dydsnew, dzdsnew
        real(fp) :: xtemp, ztemp
        integer :: i

        kx = 0.0; ky = 0.0; kz = 0.0
        kx(0) = dxds
        ky(0) = dyds
        kz(0) = dzds
        do i = 1, 5
            xtemp = x + h*dot_product(kx(0:i-1), b(0:i-1,i))
            ztemp = z + h*dot_product(kz(0:i-1), b(0:i-1,i))
            call derivs(xtemp, ztemp, kx(i), ky(i), kz(i))
        enddo
        xout = x + h*dot_product(kx(2:5), b(2:5,6)) + h*kx(0)*b(0,6)
        zout = z + h*dot_product(kz(2:5), b(2:5,6)) + h*kz(0)*b(0,6)

        call derivs(xout, zout, dxdsnew, dydsnew, dzdsnew)

        kx(6) = dxdsnew
        ky(6) = dydsnew
        kz(6) = dzdsnew
    end subroutine push

    !---------------------------------------------------------------------------
    ! Get the 2D grid indices for one point.
    ! Input:
    !   x, z: the coordinates of the point.
    !   dx, dz: the grid sizes.
    ! Return:
    !   ix1, iz1: grid indices for the bottom left corner.
    !   ix2, iz2: grid indices for the top right corner.
    !   shiftx, shifty: the offsets from the bottom left corner.
    !---------------------------------------------------------------------------
    subroutine grid_indices(x, z, dx, dz, ix1, iz1, ix2, iz2, shiftx, shiftz)
        implicit none
        real, intent(in) :: x, z, dx, dz
        integer, intent(out) :: ix1, ix2, iz1, iz2
        real, intent(out) :: shiftx, shiftz

        ix1 = floor(x / dx)
        iz1 = floor(z / dz)
        ix2 = ix1 + 1
        iz2 = iz1 + 1
        shiftx = x/dx - ix1
        shiftz = z/dz - iz1
    end subroutine grid_indices

    !---------------------------------------------------------------------------
    ! Get the direction of the filed line at current point.
    ! Input:
    !   x, z: the coordinates of the this point.
    ! Return:
    !   deltax, deltay, deltaz: the 3 directions of the field.
    !---------------------------------------------------------------------------
    subroutine derivs(x, z, deltax, deltay, deltaz)
        use constants, only: fp
        implicit none
        real(fp), intent(in) :: x, z
        real(fp), intent(out) :: deltax, deltay, deltaz
        real(fp) :: shiftx, shiftz, v1, v2, v3, v4
        real(fp) :: bx0, by0, bz0, absB
        integer :: ix1, ix2, iz1, iz2

        call grid_indices(x, z, gdx, gdz, ix1, iz1, ix2, iz2, shiftx, shiftz)
        v1 = (1.0-shiftx) * (1.0-shiftz)
        v2 = shiftx * (1.0-shiftz)
        v3 = shiftx * shiftz
        v4 = (1.0-shiftx) * shiftz

        if (ix1 >=0 .and. ix1 < nx .and. ix2 >=0 .and. ix2 < nx .and. &
                iz1 >= 0 .and. iz1 < nz .and. iz2 >= 0 .and. iz2 < nz) then
            bx0 = Bx(ix1,iz1)*v1 + Bx(ix1,iz2)*v2 + Bx(ix2,iz2)*v3 + Bx(ix2,iz1)*v4
            by0 = By(ix1,iz1)*v1 + By(ix1,iz2)*v2 + By(ix2,iz2)*v3 + By(ix2,iz1)*v4
            bz0 = Bz(ix1,iz1)*v1 + Bz(ix1,iz2)*v2 + Bz(ix2,iz2)*v3 + Bz(ix2,iz1)*v4
            absB = sqrt(bx0**2 + bz0**2)
            deltax = bx0 / absB
            deltaz = bz0 / absB
            deltay = by0 * sqrt(deltax**2+deltaz**2) / absB
        else
            deltax = 0.1
            deltay = 0.1
            deltaz = 0.1
        endif
        !if (isnan(deltax) .or. isnan(deltay) .or. isnan(deltaz)) then
        !    print*, Bx(ix1,iz1), Bx(ix1,iz2),  Bx(ix2,iz2), Bx(ix2,iz1)
        !endif
    end subroutine derivs

    !---------------------------------------------------------------------------
    ! Cash-Karp parameters for rk45.
    !---------------------------------------------------------------------------
    subroutine Cash_Karp_parameters
        implicit none
        a = 0.0
        c = 0.0
        dc = 0.0
        a(0:5) = (/ 0.0, 0.2, 0.3, 0.6, 1.0, 0.875 /)
        c(0:5) = (/ 37.0/378.0, 0.0, 250.0/621.0, 125.0/594.0, 0.0, 512.0/1771.0 /)
        dc(0:5) = (/ c(0)-2825.0/27648.0, c(1)-0.0, c(2)-18575.0/48384.0, &
                c(3)-13525.0/55296.0, c(4)-277.00/14336.0, c(5)-0.25 /)
        b = 0.0
        b(0,1) = 0.2
        b(0,2) = 3.0/40.0
        b(1,2) = 9.0/40.0
        b(0,3) = 0.3
        b(1,3) = -0.9
        b(2,3) = 1.2
        b(0,4) = -11.0/54.0
        b(1,4) = 2.5
        b(2,4) = -70.0/27.0
        b(3,4) = 35.0/27.0
        b(0,5) = 1631.0/55296.0
        b(1,5) = 175.0/512.0
        b(2,5) = 575.0/13824.0
        b(3,5) = 44275.0/110592.0
        b(4,5) = 253.0/4096.0
        b(0,6) = 37.0/378.0
        b(1,6) = 0.0
        b(2,6) = 250.0/621.0
        b(3,6) = 125.0/594.0
        b(4,6) = 0.0
        b(5,6) = 512.0/1771.0
    end subroutine Cash_Karp_parameters

    !---------------------------------------------------------------------------
    ! Dormand-Prince parameters for rk45.
    !---------------------------------------------------------------------------
    subroutine Dormand_Prince_parameters
        implicit none
        a = (/ 0.0, 0.2, 0.3, 0.8, 8.0/9.0, 1.0, 1.0 /)
        c = (/ 35.0/384.0, 0.0, 500.0/1113.0, 125.0/192.0, -2187.0/6784.0, &
            11.0/84.0, 0.0 /)
        dc = (/ c(0)-5179.0/57600.0, c(1)-0.0, c(2)-7571.0/16695.0, &
            c(3)-393.0/640.0, c(4)+92097.0/339200.0, c(5)-187.0/2100.0, c(6)-1.0/40.0/)
        b = 0.0
        b(0,1) = 0.2
        b(0,2) = 3.0/40.0
        b(1,2) = 9.0/40.0
        b(0,3) = 44.0/45.0
        b(1,3) = -56.0/15.0
        b(2,3) = 32.0/9.0
        b(0,4) = 19372.0/6561.0
        b(1,4) = -25360.0/2187.0
        b(2,4) = 64448.0/6561.0
        b(3,4) = -212.0/729.0
        b(0,5) = 9017.0/3168.0
        b(1,5) = -355.0/33.0
        b(2,5) = 46732.0/5247.0
        b(3,5) = 49.0/176.0
        b(4,5) = -5103.0/18656.0
        b(0,6) = 35.0/384.0 
        b(1,6) = 0.0
        b(2,6) = 500.0/1113.0 
        b(3,6) = 125.0/192.0
        b(4,6) = -2187.0/6784.0
        b(5,6) = 11.0/84.0
    end subroutine Dormand_Prince_parameters
end module fieldline_tracing
